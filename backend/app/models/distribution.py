from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class DistributionPlanRequest(BaseModel):
    location: str = Field(
        ...,
        description="Target location for the distribution planning (e.g., state or region).",
        examples=["India", "Maharashtra, India"]
    )
    time_horizon: str = Field(
        default="long",
        description="Forecast range: short, medium, or long."
    )

class DistributionPlanResponse(BaseModel):
    status: str
    plan: Dict[str, Any]
    meta: Dict[str, Any]
