from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class TimeHorizon(str, Enum):
    short = "short"
    medium = "medium"
    long = "long"


class SurveillanceRequest(BaseModel):
    location: str = Field(
        ...,
        description="City, region, or 'City, Country' string",
        examples=["Mumbai, India", "London, UK", "New York, US"],
    )
    time_horizon: TimeHorizon = Field(
        default=TimeHorizon.long,
        description="Forecast range: short (1-3 days), medium (7-14 days), or long (30-90 days)."
    )

class GeoResponse(BaseModel):
    city:    str
    country: str
    state:   Optional[str] = None
    lat:     float
    lon:     float
