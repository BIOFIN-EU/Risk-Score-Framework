from pydantic import BaseModel
from uuid import UUID
from typing import Dict, Any, Optional
from decimal import Decimal

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

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

class RasterSummaryStats(BaseModel):
    """Summary statistics for the raster data"""
    mean_habitat_suitability: float
    std_habitat_suitability: float

    class Config:
        schema_extra = {
            "example": {
                "mean_habitat_suitability": 0.45,
                "std_habitat_suitability": 0.12
            }
        }

class RasterDataResponse(BaseModel):
    """Raster data as a 2D list of floats"""
    raster: List[List[float]] = Field(..., description="2D array of raster values")
    summary_stats: RasterSummaryStats

    class Config:
        schema_extra = {
            "example": {
                "raster": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
                "summary_stats": {
                    "mean_habitat_suitability": 0.35,
                    "std_habitat_suitability": 0.18
                }
            }
        }

class PeriodData(BaseModel):
    """Data for a specific time period"""
    raster_data: RasterDataResponse

class ScenarioData(BaseModel):
    """Data for a specific scenario"""
    periods: Dict[str, PeriodData]

class SpeciesRichnessSuitabilityIndexResponse(BaseModel):
    """Main response schema for species richness index"""
    species: str
    country: str
    scenario: str = Field(..., description="The climate scenario (e.g., ssp245)")
    period: str = Field(..., description="The time period (e.g., 2021-2040)")
    raster_data: RasterDataResponse
    meta: Dict[str, Any] = Field(..., description="Raster metadata")

    class Config:
        schema_extra = {
            "example": {
                "species": "Lullula arborea",
                "country": "LU",
                "scenario": "ssp245",
                "period": "2021-2040",
                "raster_data": {
                    "raster": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
                    "summary_stats": {
                        "mean_habitat_suitability": 0.35,
                        "std_habitat_suitability": 0.18
                    }
                },
                "meta": {
                    "driver": "GTiff",
                    "dtype": "float32",
                    "width": 233,
                    "height": 170,
                    "crs": "GEOGCS[\"WGS 84\",...]"
                }
            }
        }
