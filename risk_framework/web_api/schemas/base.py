from pydantic import BaseModel
from typing import Optional

from pydantic import BaseModel, Field
from typing import Optional

from risk_framework.web_api.schemas.rasters import RasterDataResponse


class BaseScoreIndexRequest(BaseModel):
    country_code: str
    wkt_polygon: Optional[str] = None  # Optional
    class Config:
        schema_extra = {
            "example": {
                "country_code": "LU",
                "wkt_polygon": "POLYGON((34.5 -5.5, 34.5 5.5, 41.5 5.5, 41.5 -5.5, 34.5 -5.5))"
            }
        }

class BaseFutureScoreIndexRequest(BaseScoreIndexRequest):
    climate_scenario: str = Field(..., description="The climate scenario (e.g., ssp245)")
    climate_model: str = Field(..., description="The climate model used in calculations (e.g., EC-Earth3-Veg)")
    period: str = Field(..., description="The time period (e.g., 2021-2040)")

    class Config(BaseScoreIndexRequest.Config):
        schema_extra = BaseScoreIndexRequest.Config.schema_extra.copy()
        schema_extra['example'].update({
            "climate_scenario": "ssp245",
            "climate_model": "EC-Earth3-Veg",
            "period": "2021-2040",
        })



class BaseRasterScoreIndexResponse(BaseModel):
    id: str
    country_code: str
    geometry: str
    raster_data: RasterDataResponse

    class Config:
        schema_extra = {
            "example": {
                "id": 'abc-...-123',
                "country_code": "LU",
                "geometry": "POLYGON((34.5 -5.5, 34.5 5.5, 41.5 5.5, 41.5 -5.5, 34.5 -5.5))",
                "raster_data": RasterDataResponse.Config.schema_extra['example']
            }
        }

class BaseClimateRasterScoreIndexResponse(BaseRasterScoreIndexResponse):
    climate_scenario: Optional[str] = Field(None, description="The climate scenario (e.g., ssp245)")
    climate_model: str = Field(..., description="The climate model used in calculations (e.g., EC-Earth3-Veg)")
    period: str = Field(..., description="The time period (e.g., 2021-2040)")

    class Config(BaseRasterScoreIndexResponse.Config):
        schema_extra = BaseRasterScoreIndexResponse.Config.schema_extra.copy()
        schema_extra['example'].update({
            "climate_model": "EC-Earth3-Veg",
            "climate_scenario": "ssp245",
            "period": "2021-2040",
        })
