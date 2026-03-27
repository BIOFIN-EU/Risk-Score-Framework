from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from risk_framework.web_api.schemas import (
    CurrentBiodiversityRiskIndexRequest,
    BiodiversityRiskIndexResponse,
)
from risk_framework.web_api.utils import (
    get_db,
    generate_geo_uuid,
)
from risk_framework.web_api.models.db_operations import (
    retrieve_or_calculate_risk_future_or_current,
)



risk_router = APIRouter()

@risk_router.post("/current/", response_model=BiodiversityRiskIndexResponse)
async def calculate_current_biodiversity_risk_index(request: CurrentBiodiversityRiskIndexRequest, db: Session = Depends(get_db)):
    """
    Calculate current Biodiversity Loss Risk Index for a given country and optional area polygon.

    Args:
        request: CurrentBiodiversityRiskIndexRequest containing:
            - country_code: ISO 3166-1 alpha-2 country code (e.g., 'BR', 'US')
            - wkt_polygon: Optional WKT (Well-Known Text) polygon string to restrict calculation area
            - crop_to_polygon: True/False, if should crop result raster to wkt_polygon area.
            - risk_model: YangEtAl2021 or SihamEtAl2026 or PontesEtAl2026 - determines the risk model used for the calculation.
            - sri_logic_type: 'fuzzy' or 'crisp' - determines calculation methodology for the SRI component.
            - sri_correction_method: Optional correction method to apply to the SRI component. Currently only supports None, or HFI
            - sri_override_species_list: Optional custom species list to use for SRI calculation instead of defaults

    Returns:
    - JSON dictionary containing the Biodiversity Loss Risk Index result
    """
    climate_scenario = 'current'
    period = climate_scenario
    climate_model = None
    sri_logic_type = request.sri_logic_type
    sri_correction_method = request.sri_correction_method
    sri_override_species_list = request.sri_override_species_list
    crop_to_polygon = request.crop_to_polygon
    risk_model = request.risk_model
    geo_id = generate_geo_uuid(
        request.country_code,
        request.wkt_polygon
    )
    return retrieve_or_calculate_risk_future_or_current(
        request.country_code,
        request.wkt_polygon,
        geo_id,
        climate_scenario,
        climate_model,
        period,
        sri_logic_type,
        sri_correction_method,
        sri_override_species_list,
        crop_to_polygon,
        risk_model,
        db,
        future=False
    )


# @sri_router.post("/future/", response_model=BiodiversityRiskResponse)
# async def predict_future_species_richness_index(request: FutureSpeciesRichnessIndexRequest, db: Session = Depends(get_db)):
#     """
#     Calculate future Species Richness Index for a given country and optional area polygon.

#     Args:
#         request: FutureSpeciesRichnessIndexRequest containing:
#             - country_code: ISO 3166-1 alpha-2 country code (e.g., 'BR', 'US')
#             - wkt_polygon: Optional WKT (Well-Known Text) polygon string to restrict calculation area
#             - climate_scenario: The climate scenario (e.g., 'ssp245', 'ssp585')
#             - climate_model: The climate model used in calculations (e.g., 'EC-Earth3-Veg')
#             - period: The time period (e.g., '2021-2040', '2041-2060')
#             - logic_type: 'fuzzy' or 'crisp' - determines calculation methodology
#             - correction_method: Optional correction method to apply. Currently only supports None, or HFI
#             - override_species_list: Optional comma-separated list of species to use instead of defaults (e.g., 'Anthus trivialis,Columba palumbus')

#     Returns:
#         JSON dictionary containing the future Species Richness Index result
#     """
#     climate_scenario = request.climate_scenario
#     period = request.period
#     climate_model = request.climate_model
#     logic_type = request.logic_type
#     correction_method = request.correction_method
#     geo_id = generate_geo_uuid(
#         request.country_code,
#         request.wkt_polygon
#     )
#     return retrieve_or_calculate_sri_future_or_current(
#         request.override_species_list,
#         request.country_code,
#         request.wkt_polygon,
#         geo_id,
#         climate_scenario,
#         climate_model,
#         period,
#         logic_type,
#         correction_method,
#         db,
#         future=False
#     )

