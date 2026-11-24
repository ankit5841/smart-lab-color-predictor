from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class ColorMatchRequest(BaseModel):
    fabric_type: Literal["cotton", "polyester", "viscose", "linen", "nylon", "acetate"] = Field(
        ..., description="Textile substrate being dyed"
    )
    fabric_gsm: int = Field(
        ..., ge=50, le=600, description="Fabric weight in grams per square meter (GSM)"
    )
    liquor_ratio: str = Field(
        default="1:10",
        pattern=r"^\d+:\d+$",
        description="Dye bath liquor ratio in format 1:N (e.g., 1:8, 1:10)",
    )
    dye_class: Literal["auto", "reactive", "disperse"] = Field(
        default="auto",
        description="Auto-maps polyester/nylon/acetate to Vibrasperse Disperse and cellulosics to Chroma Reactive",
    )
    require_zdhc_bluesign: bool = Field(
        default=True,
        description="Filter historical matches to ZDHC Gateway Level 3 and bluesign approved recipes",
    )
    target_L: float = Field(..., ge=0.0, le=100.0, description="CIE L* lightness value (0 to 100)")
    target_a: float = Field(..., ge=-128.0, le=127.0, description="CIE a* green-to-red axis")
    target_b: float = Field(..., ge=-128.0, le=127.0, description="CIE b* blue-to-yellow axis")


class DyeRecipeOutput(BaseModel):
    prediction_id: Optional[int] = Field(default=None, description="Database log ID for lab feedback")
    prediction_source: Literal["openai", "deterministic_fallback"] = Field(
        default="deterministic_fallback",
        description="Engine that generated the formulation",
    )
    dye_class: Literal["reactive", "disperse"]
    product_range: str = Field(..., description="Spectrum Dyes product line (Vibrasperse or Chroma)")
    red_dye_pct: float = Field(..., description="Red dye percentage on weight of fabric (% owf)")
    yellow_dye_pct: float = Field(..., description="Yellow dye percentage on weight of fabric (% owf)")
    blue_dye_pct: float = Field(..., description="Blue dye percentage on weight of fabric (% owf)")
    salt_g_per_l: float = Field(..., description="Electrolyte/Glauber salt concentration in g/L")
    soda_ash_g_per_l: float = Field(..., description="Alkali/soda ash concentration in g/L")
    dispersing_agent_g_per_l: float = Field(..., description="Dispersing agent concentration in g/L")
    bath_ph: float = Field(..., description="Target dye bath pH")
    temperature_c: int = Field(..., description="Dyeing bath temperature in Celsius")
    expected_delta_e: float = Field(..., description="Estimated CIE76 Delta E shade tolerance")
    confidence_score: float = Field(..., description="Dynamic confidence score (0.0 to 1.0)")
    estimated_lab_trials: int = Field(..., description="Estimated lab dips required to approve shade")
    zdhc_level3_compliant: bool
    bluesign_approved: bool
    nearest_recipe_code: str
    technical_notes: str


class LabFeedbackRequest(BaseModel):
    actual_delta_e: float = Field(..., ge=0.0, le=100.0, description="Measured spectrophotometer Delta E")
    actual_lab_trials: int = Field(..., ge=1, le=20, description="Actual manual lab dips performed")


class PredictionLogSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dye_class: str
    product_range: str
    fabric_type: str
    fabric_gsm: int
    liquor_ratio: str
    expected_delta_e: float
    confidence_score: float
    actual_delta_e: Optional[float]
    actual_lab_trials: Optional[int]
    created_at: datetime


class ModelEvaluationResponse(BaseModel):
    evaluated_samples: int
    within_tolerance_count: int
    accuracy_pct: float
    mean_delta_e_error: float
    baseline_avg_manual_trials: float
    predicted_avg_lab_trials: float
    lab_trial_reduction_pct: float
