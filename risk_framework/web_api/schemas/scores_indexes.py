from pydantic import BaseModel
from uuid import UUID
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
    country_code: str
    geometry: str
    climate_scenario: str = Field(..., description="The climate scenario (e.g., ssp245)")
    climate_model: str = Field(..., description="The climate model used in calculations (e.g., EC-Earth3-Veg)")
    period: str = Field(..., description="The time period (e.g., 2021-2040)")
    raster_data: RasterDataResponse

    class Config:
        schema_extra = {
            "example": {
                "country_code": "LU",
                "geometry": "POLYGON((34.5 -5.5, 34.5 5.5, 41.5 5.5, 41.5 -5.5, 34.5 -5.5))",
                "climate_model": "EC-Earth3-Veg",
                "climate_scenario": "ssp245",
                "period": "2021-2040",
                "raster_data": RasterDataResponse.Config.schema_extra['example']
            }
        }


class CurrentSpeciesHabitatSuitabilityIndexRequest(BaseScoreIndexRequest):
    species: str
    class Config(BaseScoreIndexRequest.Config):
        schema_extra = BaseScoreIndexRequest.Config.schema_extra.copy()
        schema_extra['example'].update({
            "species": "Lullula arborea",
        })


class FutureSpeciesHabitatSuitabilityIndexRequest(BaseFutureScoreIndexRequest):
    species: str
    class Config(BaseFutureScoreIndexRequest.Config):
        schema_extra = BaseFutureScoreIndexRequest.Config.schema_extra.copy()
        schema_extra['example'].update({
            "species": "Lullula arborea",
        })



class SpeciesHabitatSuitabilityIndexResponse(BaseRasterScoreIndexResponse):
    """Main response schema for SpeciesHabitatSuitabilityIndex:
    """
    species: str

    class Config(BaseRasterScoreIndexResponse.Config):
        schema_extra = BaseRasterScoreIndexResponse.Config.schema_extra.copy()
        schema_extra['example'].update({
            "species": "Lullula arborea",
        })


class CurrentSpeciesRichnessIndexRequest(BaseScoreIndexRequest):
    override_species_list: Optional[str] = Field(
        None,
        description="Comma-separated list of Indicator Species to be used during calculation instead of the default ones (e.g., 'Anthus trivialis,Columba palumbus')"
    )
    logic_type: str = Field(
        ...,
        description="The type of logic used for the calculation (i.e., 'fuzzy' or 'crisp')"
    )
    correction_method: Optional[str] = Field(
        None,
        description="The type of correction method used. Options are HFI or null"
    )

    class Config(BaseFutureScoreIndexRequest.Config):
        schema_extra = BaseFutureScoreIndexRequest.Config.schema_extra.copy()
        schema_extra['example'].update({
            "override_species_list": "Anthus trivialis,Columba palumbus",
            "logic_type": "fuzzy",
            "correction_method": "HFI",
        })

class FutureSpeciesRichnessIndexRequest(BaseFutureScoreIndexRequest):
    override_species_list: Optional[str] = Field(
        None,
        description="Comma-separated list of Indicator Species to be used during calculation instead of the default ones (e.g., 'Anthus trivialis,Columba palumbus')"
    )
    logic_type: str = Field(
        ...,
        description="The type of logic used for the calculation (i.e., 'fuzzy' or 'crisp')"
    )
    correction_method: Optional[str] = Field(
        None,
        description="The type of correction method used. Options are HFI or null"
    )

    class Config(BaseFutureScoreIndexRequest.Config):
        schema_extra = BaseFutureScoreIndexRequest.Config.schema_extra.copy()
        schema_extra['example'].update({
            "override_species_list": "Anthus trivialis,Columba palumbus",
            "logic_type": "fuzzy",
            "correction_method": "HFI",
        })

class SpeciesRichnessIndexResponse(BaseRasterScoreIndexResponse):
    """Main response schema for SpeciesRichnessIndexResponse:
    """
    species_list: str = Field(..., description="Comma-separated list of Indicator Species used during calculation (e.g., 'Anthus trivialis,Columba palumbus')")
    logic_type: str = Field(
        ...,
        description="The type of logic used for the calculation (i.e., 'fuzzy' or 'crisp')"
    )
    correction_method: Optional[str] = Field(
        None,
        description="The type of correction method used. (i.e., 'HFI' or null)"
    )
    class Config(BaseRasterScoreIndexResponse.Config):
        schema_extra = BaseRasterScoreIndexResponse.Config.schema_extra.copy()
        schema_extra['example'].update({
            "species_list": "Anthus trivialis,Columba palumbus",
            "logic_type": "fuzzy",
            "correction_method": "HFI",
        })
