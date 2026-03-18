from sqlalchemy.orm import Session, joinedload
from fastapi import FastAPI, HTTPException, APIRouter, Depends

from risk_framework.web_api.schemas import (
    FutureSpeciesHabitatSuitabilityIndexRequest,
    CurrentSpeciesHabitatSuitabilityIndexRequest,
    SpeciesHabitatSuitabilityIndexResponse,
    CurrentSpeciesRichnessIndexRequest,
    SpeciesRichnessIndexResponse,
)
from risk_framework.web_api.utils import (
    get_db,
    generate_geo_uuid,
)
from risk_framework.web_api.models.db_operations import (
    retrieve_or_calculate_hsi_future_or_current,
    retrieve_or_calculate_sri_future_or_current,
)



hsi_router = APIRouter()



@hsi_router.post("/predict-future-habitat-suitability/", response_model=SpeciesHabitatSuitabilityIndexResponse)
async def predict_future_species_habitat_suitability_index(request: FutureSpeciesHabitatSuitabilityIndexRequest, db: Session = Depends(get_db)):
    """
    Predict future species habitat suitability index based on species name, country code, climate scenario, model and period
    and optional WKT polygon.

    Parameters:
    - **species_name**: Scientific name of the species
    - **country_code**: ISO country code
    - **wkt_polygon**: Optional WKT (Well-Known Text) polygon string
    - **climate_scenario**: climate scenario string
    - **climate_model**: climate model string
    - **period**: period (eg: 2021-2040) string
    Returns:
    - JSON dictionary containing the species habitat suitability index results
    """
    geo_id = generate_geo_uuid(
        request.country_code,
        request.wkt_polygon
    )
    return retrieve_or_calculate_hsi_future_or_current(request.species, request.country_code, request.wkt_polygon, geo_id, request.climate_scenario, request.climate_model, request.period, db, future=True)


@hsi_router.post("/calculate-current-habitat-suitability/", response_model=SpeciesHabitatSuitabilityIndexResponse)
async def calculate_current_species_habitat_suitability_index(request: CurrentSpeciesHabitatSuitabilityIndexRequest, db: Session = Depends(get_db)):
    """
    Calculate current species habitat suitability index based on species name, country code,
    and optional WKT polygon.

    Parameters:
    - **species_name**: Scientific name of the species
    - **country_code**: ISO country code
    - **wkt_polygon**: Optional WKT (Well-Known Text) polygon string
    Returns:
    - JSON dictionary containing the species habitat suitability index results
    """
    climate_scenario = 'current'
    period = climate_scenario
    climate_model = None
    geo_id = generate_geo_uuid(
        request.country_code,
        request.wkt_polygon
    )
    return retrieve_or_calculate_hsi_future_or_current(request.species, request.country_code, request.wkt_polygon, geo_id, climate_scenario, climate_model, period, db, future=False)




sri_router = APIRouter()


@sri_router.post("/calculate-current-species-richness-index/", response_model=SpeciesRichnessIndexResponse)
async def calculate_current_species_richness_index(request: CurrentSpeciesRichnessIndexRequest, db: Session = Depends(get_db)):
    """
    Calculate current Species Richness Index for a given country and optional area polygon.

    Args:
        request: CurrentSpeciesRichnessIndexRequest containing:
            - country_code: ISO 3166-1 alpha-2 country code (e.g., 'BR', 'US')
            - wkt_polygon: Optional WKT (Well-Known Text) polygon string to restrict calculation area
            - logic_type: 'fuzzy' or 'crisp' - determines calculation methodology
            - correction_method: Optional correction method to apply. Currently only supports None, or HFI
            - override_species_list: Optional custom species list to use instead of defaults

    Returns:
    - JSON dictionary containing the Species Richness Index result
    """
    climate_scenario = 'current'
    period = climate_scenario
    climate_model = None
    logic_type = request.logic_type
    correction_method = request.correction_method
    geo_id = generate_geo_uuid(
        request.country_code,
        request.wkt_polygon
    )
    return retrieve_or_calculate_sri_future_or_current(
        request.override_species_list,
        request.country_code,
        request.wkt_polygon,
        geo_id,
        climate_scenario,
        climate_model,
        period,
        logic_type,
        correction_method,
        db,
        future=False
    )
