import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.database import RecipePredictionLog, get_db, init_db
from app.predictor import (
    evaluate_historical_accuracy,
    find_nearest_historical_recipes,
    generate_recipe_prediction,
)
from app.schemas import (
    ColorMatchRequest,
    DyeRecipeOutput,
    LabFeedbackRequest,
    ModelEvaluationResponse,
    PredictionLogSummary,
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("smartlab.api")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(provided_key: Optional[str] = Security(api_key_header)) -> None:
    expected_key = os.getenv("SMARTLAB_API_KEY")
    if expected_key and provided_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header",
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Initializing Smart-Lab database and historical dye recipes...")
    init_db()
    yield
    logger.info("Shutting down Smart-Lab API.")


app = FastAPI(
    title="Smart-Lab Predictive Color-Matching API",
    description=(
        "Production-grade predictive dye formulation service aligned with Spectrum Dyes & Chemicals "
        "(Vibrasperse Disperse & Chroma Reactive ranges) with CIE LAB matching, "
        "OpenAI structured outputs, graceful fallback, and live evaluation metrics."
    ),
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_observability_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
    logger.info(
        "req_id=%s method=%s path=%s status=%s latency_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "smart-lab-predictor", "version": "2.1.0"}


@app.post(
    "/api/v1/predict-recipe",
    response_model=DyeRecipeOutput,
    dependencies=[Depends(verify_api_key)],
)
async def predict_dye_recipe(request: ColorMatchRequest, db: Session = Depends(get_db)):
    prediction = generate_recipe_prediction(db, request)

    log_entry = RecipePredictionLog(
        dye_class=prediction.dye_class,
        product_range=prediction.product_range,
        fabric_type=request.fabric_type,
        fabric_gsm=request.fabric_gsm,
        liquor_ratio=request.liquor_ratio,
        target_L=request.target_L,
        target_a=request.target_a,
        target_b=request.target_b,
        red_dye_pct=prediction.red_dye_pct,
        yellow_dye_pct=prediction.yellow_dye_pct,
        blue_dye_pct=prediction.blue_dye_pct,
        salt_g_per_l=prediction.salt_g_per_l,
        soda_ash_g_per_l=prediction.soda_ash_g_per_l,
        dispersing_agent_g_per_l=prediction.dispersing_agent_g_per_l,
        bath_ph=prediction.bath_ph,
        temperature_c=prediction.temperature_c,
        expected_delta_e=prediction.expected_delta_e,
        confidence_score=prediction.confidence_score,
        estimated_lab_trials=prediction.estimated_lab_trials,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    prediction.prediction_id = log_entry.id
    return prediction


@app.post("/api/v1/nearest-matches")
async def get_nearest_historical_shades(
    request: ColorMatchRequest, db: Session = Depends(get_db)
) -> List[dict]:
    return find_nearest_historical_recipes(db, request, top_k=3)


@app.get("/api/v1/predictions", response_model=List[PredictionLogSummary])
async def list_recent_predictions(limit: int = 20, db: Session = Depends(get_db)):
    return (
        db.query(RecipePredictionLog)
        .order_by(RecipePredictionLog.created_at.desc())
        .limit(limit)
        .all()
    )


@app.post(
    "/api/v1/predictions/{prediction_id}/feedback",
    response_model=PredictionLogSummary,
    dependencies=[Depends(verify_api_key)],
)
async def submit_lab_feedback(
    prediction_id: int, feedback: LabFeedbackRequest, db: Session = Depends(get_db)
):
    log_entry = db.query(RecipePredictionLog).filter(RecipePredictionLog.id == prediction_id).first()
    if not log_entry:
        raise HTTPException(status_code=404, detail="Prediction log not found")
    log_entry.actual_delta_e = feedback.actual_delta_e
    log_entry.actual_lab_trials = feedback.actual_lab_trials
    db.commit()
    db.refresh(log_entry)
    return log_entry


@app.get("/api/v1/metrics/evaluate", response_model=ModelEvaluationResponse)
async def get_model_evaluation_metrics(db: Session = Depends(get_db)):
    return evaluate_historical_accuracy(db)
