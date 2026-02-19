from pydantic import BaseModel
from uuid import UUID
from typing import Dict, Any, Optional
from decimal import Decimal


class SpeciesRichnessSuitabilityIndexRequest(BaseModel):
    species_name: str
    country_code: str
    wkt_poligon: Optional[str] = None  # Optional

    class Config:
        schema_extra = {
            "example": {
                "species_name": "Lullula arborea",
                "country_code": "LU",
                "wkt_poligon": "POLYGON((34.5 -5.5, 34.5 5.5, 41.5 5.5, 41.5 -5.5, 34.5 -5.5))"
            }
        }

class SpeciesRichnessSuitabilityIndex(BaseModel):
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
