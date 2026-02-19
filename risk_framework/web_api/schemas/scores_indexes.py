from pydantic import BaseModel
from uuid import UUID
from typing import Dict, Any
from decimal import Decimal

class SpeciesSuitabilityIndex(BaseModel):
    id: str
    geo_id: UUID
    value_raster_id: str
    explainability_raster_id: str
    species: str
    country_code: str
    climate_scenario: str
    climate_model: str
    period: str
    has_humam_footprint: bool
    mean_value: Decimal
    mean_std: Decimal
    mean_explainability: Dict[str, Any]

    class Config:
        from_attributes = True
