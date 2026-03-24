from sqlalchemy.orm import Session, joinedload
from fastapi import FastAPI, HTTPException, APIRouter, Depends

from risk_framework.web_api.schemas import (
    CriticalHabitatIndexRequest,
    CriticalHabitatIndexResponse
)
from risk_framework.web_api.utils import (
    get_db,
    generate_geo_uuid,
)
from risk_framework.web_api.models.db_operations import (
    retrieve_or_calculate_ch,
)


others_router = APIRouter()

@others_router.post("/chi/", response_model=CriticalHabitatIndexResponse)
async def calculate_critical_habitat_index(request: CriticalHabitatIndexRequest, db: Session = Depends(get_db)):
    """
    Calculate Critical Habitat Index for a given country and optional area polygon.

    Args:
        request: CurrentSpeciesRichnessIndexRequest containing:
            - country_code: ISO 3166-1 alpha-2 country code (e.g., 'BR', 'US')
            - wkt_polygon: Optional WKT (Well-Known Text) polygon string to restrict calculation area

    Returns:
    - JSON dictionary containing the Critical Habitat Index result
    """
    geo_id = generate_geo_uuid(
        request.country_code,
        request.wkt_polygon
    )
    return retrieve_or_calculate_ch(
        request.country_code,
        request.wkt_polygon,
        geo_id,
        db
    )

