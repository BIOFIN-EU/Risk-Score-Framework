from typing import Optional

from pydantic import Field
from typing import Optional, Dict, Any

from risk_framework.web_api.schemas.base import (
    BaseScoreIndexRequest,
    BaseFutureScoreIndexRequest,
    BaseClimateRasterScoreIndexResponse,
)

from risk_framework.web_api.schemas.rasters import RasterDataResponse




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

    class Config(BaseScoreIndexRequest.Config):
        schema_extra = BaseScoreIndexRequest.Config.schema_extra.copy()
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





class CurrentBiodiversityRiskIndexRequest(BaseScoreIndexRequest):
    sri_override_species_list: Optional[str] = Field(
        None,
        description="Comma-separated list of Indicator Species to be used during SRI calculation instead of the default ones (e.g., 'Anthus trivialis,Columba palumbus')"
    )
    sri_logic_type: str = Field(
        ...,
        description="The type of logic used for the SRI calculation (i.e., 'fuzzy' or 'crisp')"
    )
    sri_correction_method: Optional[str] = Field(
        None,
        description="The type of SRI correction method used. Options are HFI or null"
    )
    crop_to_polygon: bool = Field(
        ...,
        description="If should crop output raster to the WKT Polygon used."
    )
    risk_model: str = Field(
        ...,
        description="The type of risk model used for this calculation. Options are: 'YangEtAl2021', 'SihamEtAl2026', 'PontesEtAl2026'"
    )
    class Config(BaseFutureScoreIndexRequest.Config):
        schema_extra = BaseFutureScoreIndexRequest.Config.schema_extra.copy()
        schema_extra['example'].update({
            "sri_override_species_list": "Anthus trivialis,Columba palumbus",
            "sri_logic_type": "fuzzy",
            "sri_correction_method": "HFI",
            'crop_to_polygon': True,
            'risk_model': 'PontesEtAl2026',
        })



# need to add xai data here
class BiodiversityRiskIndexResponse(BaseClimateRasterScoreIndexResponse):
    """Main response schema for BiodiversityRiskIndexResponse:
    """
    raster_data_urban: RasterDataResponse
    xai_raster: RasterDataResponse


    xai_summary: Dict[str, Any] = Field(
        ...,
        description=(
            "General Explainability data as a flexible JSON/dict structure. "
            "Can contain any keys and values "
            "(e.g., xai_rules_meta, xai_humam_text, or other future structures)"
        )
    )

    risk_ling_thresholds: Dict[str, float] = Field(
        ...,
        description="Dictionary mapping linguistic risk categories to their numeric threshold values (e.g., {'low': 0.0929, 'medium-low': 0.25, 'medium': 0.5, 'medium-high': 0.75, 'high': 0.9458})"
    )

    sri_species_list: str = Field(..., description="Comma-separated list of Indicator Species used during SRI calculation (e.g., 'Anthus trivialis,Columba palumbus')")
    sri_logic_type: str = Field(
        ...,
        description="The type of logic used for the SRI calculation (i.e., 'fuzzy' or 'crisp')"
    )
    sri_correction_method: Optional[str] = Field(
        None,
        description="The type of correction method used for the SRI. (i.e., 'HFI' or null)"
    )
    crop_to_polygon:  bool = Field(
        ...,
        description="If the output raster was cropped to the WKT Polygon used."
    )
    risk_model: str = Field(
        ...,
        description="The type of risk model used for this calculation."
    )


    class Config(BaseClimateRasterScoreIndexResponse.Config):
        schema_extra = BaseClimateRasterScoreIndexResponse.Config.schema_extra.copy()
        schema_extra['example'].update({
            "raster_data_urban": RasterDataResponse.Config.schema_extra['example'],
            "sri_species_list": "Anthus trivialis,Columba palumbus",
            "sri_logic_type": "fuzzy",
            "sri_correction_method": "HFI",
            'crop_to_polygon': True,
            'risk_model': 'PontesEtAl2026',
        })

    #probably will want to add here and in SRI the URI reference to related resources (in here would be SRI, CHI and PAI)
