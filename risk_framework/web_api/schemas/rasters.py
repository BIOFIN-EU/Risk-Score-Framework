from pydantic import BaseModel, Field
from typing import Dict, Any, List

class RasterSummaryStats(BaseModel):
    """Summary statistics for the raster data"""
    mean_raster_value: float
    std_raster_value: float

    class Config:
        schema_extra = {
            "example": {
                "mean_raster_value": 0.45,
                "std_raster_value": 0.12
            }
        }

class RasterDataResponse(BaseModel):
    """Raster data as a 2D list of floats"""
    raster: List[List[float]] = Field(..., description="2D array of raster values")
    summary_stats: RasterSummaryStats
    meta: Dict[str, Any] = Field(..., description="Raster metadata")

    class Config:
        schema_extra = {
            "example": {
                "raster": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
                "summary_stats": RasterSummaryStats.Config.schema_extra['example'],
                "meta": {
                    "driver": "GTiff",
                    "dtype": "float32",
                    "width": 233,
                    "height": 170,
                    "crs": "GEOGCS[\"WGS 84\",...]"
                }
            }
        }
