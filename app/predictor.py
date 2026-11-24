import logging
import math
import os
from typing import Dict, List, Optional
from openai import OpenAI
from sqlalchemy.orm import Session
from app.database import HistoricalRecipe
from app.schemas import ColorMatchRequest, DyeRecipeOutput, ModelEvaluationResponse

logger = logging.getLogger("smartlab.predictor")


def resolve_dye_class(req: ColorMatchRequest) -> str:
    if req.dye_class != "auto":
        return req.dye_class
    return "disperse" if req.fabric_type in {"polyester", "nylon", "acetate"} else "reactive"


def parse_liquor_ratio_factor(liquor_ratio: str) -> float:
    parts = liquor_ratio.split(":")
    ratio_val = float(parts[1]) / max(float(parts[0]), 1.0)
    return round(10.0 / max(ratio_val, 1.0), 3)


def calculate_delta_e(L1: float, a1: float, b1: float, L2: float, a2: float, b2: float) -> float:
    return round(math.sqrt((L2 - L1) ** 2 + (a2 - a1) ** 2 + (b2 - b1) ** 2), 3)


def recipe_to_dict(rec: HistoricalRecipe) -> Dict:
    return {
        "recipe_code": rec.recipe_code,
        "dye_class": rec.dye_class,
        "product_range": rec.product_range,
        "fabric_type": rec.fabric_type,
        "fabric_gsm": rec.fabric_gsm,
        "liquor_ratio": rec.liquor_ratio,
        "L": rec.target_L,
        "a": rec.target_a,
        "b": rec.target_b,
        "red_pct": rec.red_dye_pct,
        "yellow_pct": rec.yellow_dye_pct,
        "blue_pct": rec.blue_dye_pct,
        "salt_gl": rec.salt_g_per_l,
        "soda_ash_gl": rec.soda_ash_g_per_l,
        "dispersing_agent_gl": rec.dispersing_agent_g_per_l,
        "bath_ph": rec.bath_ph,
        "temp_c": rec.temperature_c,
        "zdhc_level3_compliant": rec.zdhc_level3_compliant,
        "bluesign_approved": rec.bluesign_approved,
        "manual_trials_baseline": rec.manual_trials_baseline,
    }


def find_nearest_historical_recipes(
    db: Session,
    req: ColorMatchRequest,
    top_k: int = 3,
    exclude_code: Optional[str] = None,
) -> List[Dict]:
    target_dye_class = resolve_dye_class(req)
    query = db.query(HistoricalRecipe)
    if req.require_zdhc_bluesign:
        query = query.filter(
            HistoricalRecipe.zdhc_level3_compliant.is_(True),
            HistoricalRecipe.bluesign_approved.is_(True),
        )
    if exclude_code:
        query = query.filter(HistoricalRecipe.recipe_code != exclude_code)

    candidates = query.all()
    scored = []
    for rec in candidates:
        de = calculate_delta_e(req.target_L, req.target_a, req.target_b, rec.target_L, rec.target_a, rec.target_b)
        class_penalty = 0.0 if rec.dye_class == target_dye_class else 25.0
        fabric_penalty = 0.0 if rec.fabric_type == req.fabric_type else 5.0
        scored.append({
            **recipe_to_dict(rec),
            "delta_e_distance": de,
            "rank_score": round(de + class_penalty + fabric_penalty, 3),
        })

    scored.sort(key=lambda x: x["rank_score"])
    return scored[:top_k]


def generate_recipe_prediction(
    db: Session,
    req: ColorMatchRequest,
    exclude_code: Optional[str] = None,
) -> DyeRecipeOutput:
    dye_class = resolve_dye_class(req)
    product_range = "Disperse Dyes" if dye_class == "disperse" else "Reactive Dyes"
    nearest = find_nearest_historical_recipes(db, req, top_k=3, exclude_code=exclude_code)
    same_class_matches = [r for r in nearest if r["dye_class"] == dye_class] or nearest

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and exclude_code is None:
        try:
            client = OpenAI(api_key=api_key, timeout=10.0)
            system_prompt = (
                "You are a textile coloration engineer at a textile chemical manufacturer. "
                "Use Disperse Dyes (130C, acidic pH ~4.8, dispersing agent, 0 salt/soda ash) "
                "for synthetics and Reactive Dyes (60C, alkaline pH ~10.8, salt + soda ash) "
                "for cellulosics. Return a structured DyeRecipeOutput grounded in the nearest validated recipes."
            )
            user_prompt = (
                f"DyeClass={dye_class}, ProductRange={product_range}, Fabric={req.fabric_type}, "
                f"GSM={req.fabric_gsm}, LiquorRatio={req.liquor_ratio}, "
                f"Target LAB=({req.target_L}, {req.target_a}, {req.target_b}).\n"
                f"Nearest Historical Recipes: {same_class_matches}"
            )
            completion = client.beta.chat.completions.parse(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=DyeRecipeOutput,
                temperature=0.1,
            )
            parsed = completion.choices[0].message.parsed
            if parsed is not None:
                parsed.prediction_source = "openai"
                logger.info("Prediction served by OpenAI model for %s (%s)", req.fabric_type, product_range)
                return parsed
        except Exception as exc:
            logger.warning("OpenAI prediction failed (%s); falling back to deterministic CIE engine.", exc)

    lr_factor = parse_liquor_ratio_factor(req.liquor_ratio)
    weights = [1.0 / max(r["delta_e_distance"], 0.1) for r in same_class_matches]
    total_w = sum(weights)

    red = round(sum(r["red_pct"] * w for r, w in zip(same_class_matches, weights)) / total_w, 3)
    yellow = round(sum(r["yellow_pct"] * w for r, w in zip(same_class_matches, weights)) / total_w, 3)
    blue = round(sum(r["blue_pct"] * w for r, w in zip(same_class_matches, weights)) / total_w, 3)

    if dye_class == "disperse":
        salt = 0.0
        soda = 0.0
        dispersing = round(
            (sum(r["dispersing_agent_gl"] * w for r, w in zip(same_class_matches, weights)) / total_w) * lr_factor, 2
        )
        bath_ph = round(sum(r["bath_ph"] * w for r, w in zip(same_class_matches, weights)) / total_w, 2)
        temp = 130
    else:
        salt = round(
            (sum(r["salt_gl"] * w for r, w in zip(same_class_matches, weights)) / total_w) * lr_factor, 1
        )
        soda = round(
            (sum(r["soda_ash_gl"] * w for r, w in zip(same_class_matches, weights)) / total_w) * lr_factor, 1
        )
        dispersing = 0.0
        bath_ph = round(sum(r["bath_ph"] * w for r, w in zip(same_class_matches, weights)) / total_w, 2)
        temp = 60

    closest_de = same_class_matches[0]["delta_e_distance"]
    expected_de = round(closest_de * 0.22, 2)
    confidence = round(max(0.15, min(0.99, math.exp(-closest_de / 35.0))), 2)

    if expected_de <= 1.0:
        est_trials = 2
    elif expected_de <= 2.5:
        est_trials = 3
    else:
        est_trials = 4

    return DyeRecipeOutput(
        prediction_source="deterministic_fallback",
        dye_class=dye_class,
        product_range=product_range,
        red_dye_pct=red,
        yellow_dye_pct=yellow,
        blue_dye_pct=blue,
        salt_g_per_l=salt,
        soda_ash_g_per_l=soda,
        dispersing_agent_g_per_l=dispersing,
        bath_ph=bath_ph,
        temperature_c=temp,
        expected_delta_e=expected_de,
        confidence_score=confidence,
        estimated_lab_trials=est_trials,
        zdhc_level3_compliant=same_class_matches[0]["zdhc_level3_compliant"],
        bluesign_approved=same_class_matches[0]["bluesign_approved"],
        nearest_recipe_code=same_class_matches[0]["recipe_code"],
        technical_notes=(
            f"Interpolated {product_range} recipe from {same_class_matches[0]['recipe_code']} "
            f"(Delta E distance={closest_de}) scaled for {req.fabric_gsm} GSM {req.fabric_type} "
            f"at {req.liquor_ratio} liquor ratio."
        ),
    )


def evaluate_historical_accuracy(db: Session) -> ModelEvaluationResponse:
    recipes = db.query(HistoricalRecipe).all()
    if not recipes:
        return ModelEvaluationResponse(
            evaluated_samples=0,
            within_tolerance_count=0,
            accuracy_pct=0.0,
            mean_delta_e_error=0.0,
            baseline_avg_manual_trials=0.0,
            predicted_avg_lab_trials=0.0,
            lab_trial_reduction_pct=0.0,
        )

    within_tol = 0
    total_de = 0.0
    total_baseline_trials = 0
    total_predicted_trials = 0

    for rec in recipes:
        req = ColorMatchRequest(
            fabric_type=rec.fabric_type,
            fabric_gsm=rec.fabric_gsm,
            liquor_ratio=rec.liquor_ratio,
            dye_class=rec.dye_class,
            target_L=rec.target_L,
            target_a=rec.target_a,
            target_b=rec.target_b,
        )
        pred = generate_recipe_prediction(db, req, exclude_code=rec.recipe_code)
        dye_mae = (
            abs(pred.red_dye_pct - rec.red_dye_pct)
            + abs(pred.yellow_dye_pct - rec.yellow_dye_pct)
            + abs(pred.blue_dye_pct - rec.blue_dye_pct)
        ) / 3.0

        total_de += pred.expected_delta_e
        if dye_mae <= 0.35:
            within_tol += 1

        if dye_mae <= 0.15:
            actual_trials = 3
        elif dye_mae <= 0.35:
            actual_trials = 4
        else:
            actual_trials = 5

        total_baseline_trials += rec.manual_trials_baseline
        total_predicted_trials += actual_trials

    n = len(recipes)
    baseline_avg = round(total_baseline_trials / n, 2)
    predicted_avg = round(total_predicted_trials / n, 2)
    reduction_pct = round(((baseline_avg - predicted_avg) / max(baseline_avg, 1.0)) * 100.0, 2)

    return ModelEvaluationResponse(
        evaluated_samples=n,
        within_tolerance_count=within_tol,
        accuracy_pct=round((within_tol / n) * 100.0, 2),
        mean_delta_e_error=round(total_de / n, 3),
        baseline_avg_manual_trials=baseline_avg,
        predicted_avg_lab_trials=predicted_avg,
        lab_trial_reduction_pct=reduction_pct,
    )
