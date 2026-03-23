from typing import Optional

from pydantic import Field
from typing import Optional

from risk_framework.web_api.schemas.base import (
    BaseScoreIndexRequest,
    BaseFutureScoreIndexRequest,
    BaseClimateRasterScoreIndexResponse,
)




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



class SpeciesHabitatSuitabilityIndexResponse(BaseClimateRasterScoreIndexResponse):
    """Main response schema for SpeciesHabitatSuitabilityIndex:
    """
    species: str

    class Config(BaseClimateRasterScoreIndexResponse.Config):
        schema_extra = BaseClimateRasterScoreIndexResponse.Config.schema_extra.copy()
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

class SpeciesRichnessIndexResponse(BaseClimateRasterScoreIndexResponse):
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
    class Config(BaseClimateRasterScoreIndexResponse.Config):
        schema_extra = BaseClimateRasterScoreIndexResponse.Config.schema_extra.copy()
        schema_extra['example'].update({
            "species_list": "Anthus trivialis,Columba palumbus",
            "logic_type": "fuzzy",
            "correction_method": "HFI",
        })
