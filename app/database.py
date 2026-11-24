import os
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smartlab_recipes.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class HistoricalRecipe(Base):
    __tablename__ = "historical_recipes"

    id = Column(Integer, primary_key=True, index=True)
    recipe_code = Column(String, unique=True, index=True, nullable=False)
    dye_class = Column(String, index=True, nullable=False)
    product_range = Column(String, nullable=False)
    fabric_type = Column(String, index=True, nullable=False)
    fabric_gsm = Column(Integer, nullable=False)
    liquor_ratio = Column(String, default="1:10", nullable=False)
    target_L = Column(Float, nullable=False)
    target_a = Column(Float, nullable=False)
    target_b = Column(Float, nullable=False)
    red_dye_pct = Column(Float, nullable=False)
    yellow_dye_pct = Column(Float, nullable=False)
    blue_dye_pct = Column(Float, nullable=False)
    salt_g_per_l = Column(Float, nullable=False)
    soda_ash_g_per_l = Column(Float, nullable=False)
    dispersing_agent_g_per_l = Column(Float, default=0.0, nullable=False)
    bath_ph = Column(Float, nullable=False)
    temperature_c = Column(Integer, nullable=False)
    zdhc_level3_compliant = Column(Boolean, default=True, nullable=False)
    bluesign_approved = Column(Boolean, default=True, nullable=False)
    manual_trials_baseline = Column(Integer, default=5, nullable=False)


class RecipePredictionLog(Base):
    __tablename__ = "recipe_prediction_logs"

    id = Column(Integer, primary_key=True, index=True)
    dye_class = Column(String, index=True, nullable=False)
    product_range = Column(String, nullable=False)
    fabric_type = Column(String, index=True, nullable=False)
    fabric_gsm = Column(Integer, nullable=False)
    liquor_ratio = Column(String, nullable=False)
    target_L = Column(Float, nullable=False)
    target_a = Column(Float, nullable=False)
    target_b = Column(Float, nullable=False)
    red_dye_pct = Column(Float, nullable=False)
    yellow_dye_pct = Column(Float, nullable=False)
    blue_dye_pct = Column(Float, nullable=False)
    salt_g_per_l = Column(Float, nullable=False)
    soda_ash_g_per_l = Column(Float, nullable=False)
    dispersing_agent_g_per_l = Column(Float, nullable=False)
    bath_ph = Column(Float, nullable=False)
    temperature_c = Column(Integer, nullable=False)
    expected_delta_e = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=False)
    estimated_lab_trials = Column(Integer, nullable=False)
    actual_delta_e = Column(Float, nullable=True)
    actual_lab_trials = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


SEED_RECIPES = [
    # Chroma Reactive Dyes (Cellulosics: Cotton, Linen, Viscose)
    {
        "recipe_code": "CHR-101", "dye_class": "reactive", "product_range": "Chroma Reactive",
        "fabric_type": "cotton", "fabric_gsm": 180, "liquor_ratio": "1:10",
        "target_L": 42.5, "target_a": 51.2, "target_b": 18.4,
        "red_dye_pct": 2.45, "yellow_dye_pct": 0.62, "blue_dye_pct": 0.08,
        "salt_g_per_l": 60.0, "soda_ash_g_per_l": 15.0, "dispersing_agent_g_per_l": 0.0,
        "bath_ph": 10.8, "temperature_c": 60, "manual_trials_baseline": 5,
    },
    {
        "recipe_code": "CHR-102", "dye_class": "reactive", "product_range": "Chroma Reactive",
        "fabric_type": "cotton", "fabric_gsm": 195, "liquor_ratio": "1:10",
        "target_L": 44.2, "target_a": 49.0, "target_b": 16.8,
        "red_dye_pct": 2.25, "yellow_dye_pct": 0.56, "blue_dye_pct": 0.09,
        "salt_g_per_l": 58.0, "soda_ash_g_per_l": 15.0, "dispersing_agent_g_per_l": 0.0,
        "bath_ph": 10.8, "temperature_c": 60, "manual_trials_baseline": 5,
    },
    {
        "recipe_code": "CHR-103", "dye_class": "reactive", "product_range": "Chroma Reactive",
        "fabric_type": "cotton", "fabric_gsm": 165, "liquor_ratio": "1:10",
        "target_L": 28.0, "target_a": 12.5, "target_b": -38.0,
        "red_dye_pct": 0.40, "yellow_dye_pct": 0.12, "blue_dye_pct": 3.10,
        "salt_g_per_l": 70.0, "soda_ash_g_per_l": 20.0, "dispersing_agent_g_per_l": 0.0,
        "bath_ph": 11.0, "temperature_c": 60, "manual_trials_baseline": 6,
    },
    {
        "recipe_code": "CHR-104", "dye_class": "reactive", "product_range": "Chroma Reactive",
        "fabric_type": "cotton", "fabric_gsm": 170, "liquor_ratio": "1:10",
        "target_L": 29.8, "target_a": 11.2, "target_b": -36.2,
        "red_dye_pct": 0.36, "yellow_dye_pct": 0.10, "blue_dye_pct": 2.95,
        "salt_g_per_l": 68.0, "soda_ash_g_per_l": 19.0, "dispersing_agent_g_per_l": 0.0,
        "bath_ph": 11.0, "temperature_c": 60, "manual_trials_baseline": 5,
    },
    {
        "recipe_code": "CHR-105", "dye_class": "reactive", "product_range": "Chroma Reactive",
        "fabric_type": "linen", "fabric_gsm": 190, "liquor_ratio": "1:10",
        "target_L": 60.2, "target_a": 4.1, "target_b": -22.5,
        "red_dye_pct": 0.22, "yellow_dye_pct": 0.08, "blue_dye_pct": 1.45,
        "salt_g_per_l": 50.0, "soda_ash_g_per_l": 12.0, "dispersing_agent_g_per_l": 0.0,
        "bath_ph": 10.6, "temperature_c": 60, "manual_trials_baseline": 5,
    },
    {
        "recipe_code": "CHR-106", "dye_class": "reactive", "product_range": "Chroma Reactive",
        "fabric_type": "viscose", "fabric_gsm": 150, "liquor_ratio": "1:10",
        "target_L": 58.9, "target_a": 5.0, "target_b": -21.0,
        "red_dye_pct": 0.25, "yellow_dye_pct": 0.09, "blue_dye_pct": 1.52,
        "salt_g_per_l": 52.0, "soda_ash_g_per_l": 12.5, "dispersing_agent_g_per_l": 0.0,
        "bath_ph": 10.6, "temperature_c": 60, "manual_trials_baseline": 5,
    },
    # Vibrasperse Disperse Dyes (Synthetics: Polyester, Nylon)
    {
        "recipe_code": "VBS-201", "dye_class": "disperse", "product_range": "Vibrasperse Disperse",
        "fabric_type": "polyester", "fabric_gsm": 150, "liquor_ratio": "1:10",
        "target_L": 72.0, "target_a": -8.5, "target_b": 64.0,
        "red_dye_pct": 0.05, "yellow_dye_pct": 1.85, "blue_dye_pct": 0.14,
        "salt_g_per_l": 0.0, "soda_ash_g_per_l": 0.0, "dispersing_agent_g_per_l": 1.5,
        "bath_ph": 4.8, "temperature_c": 130, "manual_trials_baseline": 5,
    },
    {
        "recipe_code": "VBS-202", "dye_class": "disperse", "product_range": "Vibrasperse Disperse",
        "fabric_type": "polyester", "fabric_gsm": 160, "liquor_ratio": "1:10",
        "target_L": 70.5, "target_a": -7.2, "target_b": 61.8,
        "red_dye_pct": 0.07, "yellow_dye_pct": 1.78, "blue_dye_pct": 0.16,
        "salt_g_per_l": 0.0, "soda_ash_g_per_l": 0.0, "dispersing_agent_g_per_l": 1.5,
        "bath_ph": 4.8, "temperature_c": 130, "manual_trials_baseline": 5,
    },
    {
        "recipe_code": "VBS-203", "dye_class": "disperse", "product_range": "Vibrasperse Disperse",
        "fabric_type": "polyester", "fabric_gsm": 210, "liquor_ratio": "1:10",
        "target_L": 34.0, "target_a": 45.5, "target_b": 22.0,
        "red_dye_pct": 2.90, "yellow_dye_pct": 0.80, "blue_dye_pct": 0.15,
        "salt_g_per_l": 0.0, "soda_ash_g_per_l": 0.0, "dispersing_agent_g_per_l": 2.0,
        "bath_ph": 4.6, "temperature_c": 130, "manual_trials_baseline": 6,
    },
    {
        "recipe_code": "VBS-204", "dye_class": "disperse", "product_range": "Vibrasperse Disperse",
        "fabric_type": "polyester", "fabric_gsm": 200, "liquor_ratio": "1:10",
        "target_L": 35.6, "target_a": 43.8, "target_b": 20.5,
        "red_dye_pct": 2.75, "yellow_dye_pct": 0.74, "blue_dye_pct": 0.14,
        "salt_g_per_l": 0.0, "soda_ash_g_per_l": 0.0, "dispersing_agent_g_per_l": 2.0,
        "bath_ph": 4.6, "temperature_c": 130, "manual_trials_baseline": 5,
    },
    {
        "recipe_code": "CHR-107", "dye_class": "reactive", "product_range": "Chroma Reactive",
        "fabric_type": "cotton", "fabric_gsm": 175, "liquor_ratio": "1:10",
        "target_L": 48.0, "target_a": -34.5, "target_b": 24.0,
        "red_dye_pct": 0.12, "yellow_dye_pct": 1.65, "blue_dye_pct": 1.80,
        "salt_g_per_l": 62.0, "soda_ash_g_per_l": 16.0, "dispersing_agent_g_per_l": 0.0,
        "bath_ph": 10.8, "temperature_c": 60, "manual_trials_baseline": 5,
    },
    {
        "recipe_code": "CHR-108", "dye_class": "reactive", "product_range": "Chroma Reactive",
        "fabric_type": "cotton", "fabric_gsm": 180, "liquor_ratio": "1:10",
        "target_L": 49.5, "target_a": -32.8, "target_b": 22.6,
        "red_dye_pct": 0.14, "yellow_dye_pct": 1.55, "blue_dye_pct": 1.72,
        "salt_g_per_l": 60.0, "soda_ash_g_per_l": 16.0, "dispersing_agent_g_per_l": 0.0,
        "bath_ph": 10.8, "temperature_c": 60, "manual_trials_baseline": 5,
    },
    {
        "recipe_code": "VBS-205", "dye_class": "disperse", "product_range": "Vibrasperse Disperse",
        "fabric_type": "acetate", "fabric_gsm": 140, "liquor_ratio": "1:10",
        "target_L": 22.0, "target_a": 28.0, "target_b": -42.0,
        "red_dye_pct": 2.10, "yellow_dye_pct": 0.15, "blue_dye_pct": 3.40,
        "salt_g_per_l": 0.0, "soda_ash_g_per_l": 0.0, "dispersing_agent_g_per_l": 2.2,
        "bath_ph": 4.7, "temperature_c": 130, "manual_trials_baseline": 6,
    },
]


def seed_historical_recipes(db: Session) -> None:
    if db.query(HistoricalRecipe).count() == 0:
        for item in SEED_RECIPES:
            db.add(HistoricalRecipe(**item))
        db.commit()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_historical_recipes(db)
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
