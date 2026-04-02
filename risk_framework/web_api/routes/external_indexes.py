from sqlalchemy.orm import Session, joinedload
from fastapi import FastAPI, HTTPException, APIRouter, Depends

from risk_framework.web_api.schemas import (
    CriticalHabitatIndexRequest,
    CriticalHabitatIndexResponse,
    ProtectedAreaIndexResponse,
    ProtectedAreaIndexRequest,
)
from risk_framework.web_api.utils import (
    get_db,
    generate_geo_uuid,
)
from risk_framework.web_api.models.db_operations import (
    retrieve_or_calculate_ch,
    retrieve_or_calculate_pa,
    retrieve_ch_by_id,
    retrieve_pa_by_id
)


others_router = APIRouter()

@others_router.post("/chi/calculate/", response_model=CriticalHabitatIndexResponse)
async def calculate_critical_habitat_index(request: CriticalHabitatIndexRequest, db: Session = Depends(get_db)):
    """
    Calculate Critical Habitat Index for a given country and optional area polygon.

    Args:
        request: CriticalHabitatIndexResponse containing:
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



@others_router.get("/chi/get/{record_id}/", response_model=CriticalHabitatIndexResponse,
                name="get_chi_record")
async def get_critical_habitat_index_by_id(
    record_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific Record by its ID.

    Args:
        record_id: UUID of the record to retrieve (e.g., 1234-567...-910)

    Returns:
        A Single Index record or 404
    """
    try:
        record_output = retrieve_ch_by_id(record_id, db)
    except RuntimeError:
        raise HTTPException(status_code=404, detail=f"Record with id {record_id} not found")

    return record_output


@others_router.post("/pai/calculate/", response_model=ProtectedAreaIndexResponse)
async def calculate_protected_area_index(request: ProtectedAreaIndexRequest, db: Session = Depends(get_db)):
    """
    Calculate Protected Area Index for a given country and optional area polygon.

    Args:
        request: ProtectedAreaIndexRequest containing:
            - country_code: ISO 3166-1 alpha-2 country code (e.g., 'BR', 'US')
            - wkt_polygon: Optional WKT (Well-Known Text) polygon string to restrict calculation area

    Returns:
    - JSON dictionary containing theProtected Area Index result
    """
    geo_id = generate_geo_uuid(
        request.country_code,
        request.wkt_polygon
    )
    return retrieve_or_calculate_pa(
        request.country_code,
        request.wkt_polygon,
        geo_id,
        db
    )



@others_router.get("/pai/get/{record_id}/",
                   response_model=ProtectedAreaIndexResponse,
                name="get_pai_record")
async def get_protected_area_index_by_id(
    record_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific Record by its ID.

    Args:
        record_id: UUID of the record to retrieve (e.g., 1234-567...-910)

    Returns:
        A Single Index record or 404
    """
    try:
        record_output = retrieve_pa_by_id(record_id, db)
    except RuntimeError:
        raise HTTPException(status_code=404, detail=f"Record with id {record_id} not found")

    return record_output
