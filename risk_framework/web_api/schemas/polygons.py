from typing import Optional

from pydantic import Field
from typing import Optional, Dict, Any

from risk_framework.web_api.schemas.base import (
    BaseScoreIndexRequest,
    BaseScoreIndexResponse,
)



class PriorityManagementActionsRequest(BaseScoreIndexRequest):
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
    risk_model: str = Field(
        ...,
        description="The type of risk model used for this calculation. Options are: 'YangEtAl2021', 'SihamEtAl2026', 'PontesEtAl2026'"
    )
    risk_type: str = Field(
        ...,
        description="The type of risk used by this calculation. ('NonPA' , 'IsPA', or 'Full')"
    )
    class Config(BaseScoreIndexRequest.Config):
        schema_extra = BaseScoreIndexRequest.Config.schema_extra.copy()
        schema_extra['example'].update({
            "sri_override_species_list": "Anthus trivialis,Columba palumbus",
            "sri_logic_type": "fuzzy",
            "sri_correction_method": "HFI",
            'risk_model': 'PontesEtAl2026',
            'risk_type': 'All',
        })


class PriorityManagementActionsResponse(BaseScoreIndexResponse):
    """Main response schema for riorityManagementActions:
    """
    periods: str = Field(..., description="The time periods (e.g., 'current, 2021-2060')")

    sri_species_list: str = Field(..., description="Comma-separated list of Indicator Species used during SRI calculation (e.g., 'Anthus trivialis,Columba palumbus')")
    sri_logic_type: str = Field(
        ...,
        description="The type of logic used for the SRI calculation (i.e., 'fuzzy' or 'crisp')"
    )
    sri_correction_method: Optional[str] = Field(
        None,
        description="The type of correction method used for the SRI. (i.e., 'HFI' or null)"
    )
    risk_model: str = Field(
        ...,
        description="The type of risk model used for this calculation."
    )

    risk_type: str = Field(
        ...,
        description="The type of risk outputed by this calculation. ('NonPA' or 'IsPA')"
    )

    # Relationship URLs (required)
    risk: str = Field(
        ...,
        description="URL to retrieve the related Biodiversity Risk Index record"
    )

    resilience_polygons: Dict[str, Any] = Field(
        ...,
        description=(
            "Dictionary with polygons for each category of the climate-resilience classes "
        )
    )
    risk_polygons: Dict[str, Any] = Field(
        ...,
        description=(
            "Dictionary with polygons for each category of the biodiversity-risk classes "
        )
    )
    recommendations_polygons: Dict[str, Any] = Field(
        ...,
        description=(
            "Dictionary with polygons for each category of the recommended management actions classes "
        )
    )
    recommendations_totals: Dict[str, Any] = Field(
        ...,
        description=(
            "Dictionary with statistics for each management action class"
        )
    )
    recommendations_meta: Dict[str, Any] = Field(
        ...,
        description=(
            "Dictionary with metadata the priority management action polygons"
        )
    )
    resilience_meta: Dict[str, Any] = Field(
        ...,
        description=(
            "Dictionary with metadata the climate-resilience polygons"
        )
    )
    risk_meta: Dict[str, Any] = Field(
        ...,
        description=(
            "Dictionary with metadata the biodiversity-risk polygons"
        )
    )

    class Config(BaseScoreIndexResponse.Config):
        schema_extra = BaseScoreIndexResponse.Config.schema_extra.copy()
        schema_extra['example'].update({
            "periods": "current, 2021-2060",
            "sri_species_list": "Anthus trivialis,Columba palumbus",
            "sri_logic_type": "fuzzy",
            "sri_correction_method": "HFI",
            'risk_model': 'PontesEtAl2026',
            'risk_type': 'NonPA',
            "risk": "/api/v1/risk/get/550e8400-e29b-41d4-a716-446655440002/",
            # need to add the polygons, and meta field
        })

    #probably will want to add here and in SRI the URI reference to related resources (in here would be SRI, CHI and PAI)
