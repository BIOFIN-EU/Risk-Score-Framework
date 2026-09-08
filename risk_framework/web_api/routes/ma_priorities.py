from sqlalchemy.orm import Session, joinedload
from fastapi import APIRouter, Depends, HTTPException, Request

from risk_framework.web_api.schemas import (
    PriorityManagementActionsRequest,
    PriorityManagementActionsResponse
)
from risk_framework.web_api.utils import (
    get_db,
    generate_geo_uuid,
)
from risk_framework.web_api.models.db_operations import (
    retrieve_or_caculate_priority_management_actions,
    retrieve_priority_management_actions_by_id
)



ma_priorities_router = APIRouter()

@ma_priorities_router.post("/priority/", response_model=PriorityManagementActionsResponse)
async def calculate_priority_management_actions(request: PriorityManagementActionsRequest, db: Session = Depends(get_db)):
    """
    Calculate Priority Management Actions for a given country and optional area polygon.

    - JSON dictionary containing the Priority Management Actions result
    """
    sri_logic_type = request.sri_logic_type
    sri_correction_method = request.sri_correction_method
    sri_override_species_list = request.sri_override_species_list
    if sri_override_species_list:
        sri_override_species_list = sri_override_species_list.split(',')
    risk_model = request.risk_model
    risk_type = request.risk_type
    geo_id = generate_geo_uuid(
        request.country_code,
        request.wkt_polygon
    )

    return retrieve_or_caculate_priority_management_actions(
        geo_id,
        request.country_code,
        request.wkt_polygon,
        sri_logic_type,
        sri_correction_method,
        sri_override_species_list,
        risk_model,
        risk_type,
        db
    )


@ma_priorities_router.get("/get/{record_id}/", response_model=PriorityManagementActionsResponse, name="get_ma_priorities_record")
async def get_ma_priorities_by_id(
    record_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific Priority Management Actions record by its ID.

    Args:
        record_id: UUID of the record to retrieve (e.g. '1234-567...-910')

    Returns:
        Single Priority Management Actions record
    """
    try:
        record_output = retrieve_priority_management_actions_by_id(request, record_id, db)
    except RuntimeError:
        raise HTTPException(status_code=404, detail=f"Record with id {record_id} not found")

    return record_output
