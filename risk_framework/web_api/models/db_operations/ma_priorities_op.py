import uuid
import pickle
from urllib.parse import urlparse

from sqlalchemy.orm import joinedload

from risk_framework.web_api.models import (
    PriorityManagementActionsPolygonsDB
)
from risk_framework.web_api.schemas import (
    PriorityManagementActionsResponse,
)
from risk_framework.web_api.utils import (
    get_country_wkt
)

from risk_framework.management_actions.model_wrapper import (
    BiofinMAPriorityModelWrapper
)

from risk_framework.species_models.per_country_species_conf import (
    INDICATOR_SP_PER_COUNTRY,
)

from risk_framework.web_api.models.db_operations import (
    retrieve_or_calculate_sri_future_or_current,
    retrieve_or_calculate_risk_future_or_current
)


def retrieve_priority_management_actions_by_id(request, record_id, db):
    query = db.query(PriorityManagementActionsPolygonsDB)
    existing_record = query.filter(
        PriorityManagementActionsPolygonsDB.id == record_id
    ).first()

    if not existing_record:
        raise RuntimeError(f"PriorityManagementActionsPolygons record with id {record_id} not found")

    return calculate_priority_management_actions(
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        existing_record,
        db,
        request
    )


def retrieve_or_caculate_priority_management_actions(
        geo_id,
        country_code,
        wkt_polygon,
        sri_logic_type,
        sri_correction_method,
        sri_override_species_list,
        risk_model,
        risk_type,
        db
    ):

    country_code = country_code.upper()


    query = db.query(PriorityManagementActionsPolygonsDB)

    sri_species_list = sri_override_species_list
    if sri_override_species_list is None:
        sri_species_list = INDICATOR_SP_PER_COUNTRY.get(country_code, INDICATOR_SP_PER_COUNTRY['DEFAULT-EU'])
    sri_species_list.sort()

    sri_species_list_str = ','.join(sri_species_list)
    query = query.filter(
        PriorityManagementActionsPolygonsDB.geo_id == geo_id,
        PriorityManagementActionsPolygonsDB.sri_logic_type == sri_logic_type,
        PriorityManagementActionsPolygonsDB.sri_correction_method == sri_correction_method,
        PriorityManagementActionsPolygonsDB.sri_species_list == sri_species_list_str,
        PriorityManagementActionsPolygonsDB.risk_model == risk_model,
        PriorityManagementActionsPolygonsDB.risk_type == risk_type,
    )
    existing_record = query.first()
    # db.delete(existing_record)
    # db.commit()
    return calculate_priority_management_actions(
        geo_id,
        country_code,
        wkt_polygon,
        sri_logic_type,
        sri_correction_method,
        sri_override_species_list,
        risk_model,
        risk_type,
        existing_record,
        db,
    )


def calculate_priority_management_actions(
        geo_id,
        country_code,
        wkt_polygon,
        sri_logic_type,
        sri_correction_method,
        sri_species_list,
        risk_model,
        risk_type,
        existing_record,
        db,
        request=None
    ):
    # If record exists, retrieve it and return cached result
    if not existing_record:
        existing_record = run_and_create_new_management_action_record(
            geo_id,
            country_code,
            wkt_polygon,
            sri_logic_type,
            sri_correction_method,
            sri_species_list,
            risk_model,
            risk_type,
            db
        )

    if request:


        risk_url = urlparse(str(request.url_for("get_risk_record", record_id=existing_record.bio_risk_id))).path
    else:
        from risk_framework.web_api.core import app
        risk_url = app.url_path_for("get_risk_record", record_id=existing_record.bio_risk_id)
        # risk_url = existing_record.bio_risk_id

    response = PriorityManagementActionsResponse(
        id=existing_record.id,
        country_code=existing_record.country_code,
        geometry=existing_record.geometry,
        periods=existing_record.periods,
        climate_model=existing_record.climate_model,
        climate_scenarios="ssp245, ssp585", #hardcoding this for the moment
        risk_model=existing_record.risk_model,
        risk_type=existing_record.risk_type,
        sri_species_list=existing_record.sri_species_list,
        sri_correction_method=existing_record.sri_correction_method,
        sri_logic_type=existing_record.sri_logic_type,
        risk=risk_url,
        recommendations_polygons=existing_record.recommendations_polygons,
        resilience_polygons=existing_record.resilience_polygons,
        risk_polygons=existing_record.risk_polygons,
        recommendations_totals=existing_record.recommendations_totals,
        recommendations_meta=existing_record.polygons_meta['recommendations_meta'],
        resilience_dominant_class=existing_record.resilience_dominant_class,
        resilience_meta=existing_record.polygons_meta['resilience_meta'],
        risk_meta=existing_record.polygons_meta['risk_meta'],
        xai_summary=existing_record.xai_humam_text_json
    )

    return response

def run_and_create_new_management_action_record(
        geo_id,
        country_code,
        wkt_polygon,
        sri_logic_type,
        sri_correction_method,
        sri_species_list,
        risk_model,
        risk_type,
        db
    ):
    if wkt_polygon == "" or wkt_polygon is None:
        wkt_polygon = get_country_wkt(country_code)


    sri_retrieval_method = retrieve_or_calculate_sri_future_or_current
    risk_retrieval_method = retrieve_or_calculate_risk_future_or_current
    priority_model = BiofinMAPriorityModelWrapper(
        geo_id,
        country_code,
        wkt_polygon,
        risk_retrieval_method,
        sri_retrieval_method,
        sri_logic_type, sri_correction_method, sri_species_list,
        crop_to_polygon=True, risk_model=risk_model, risk_type=risk_type, db=db
    )
    result = priority_model.run() #climate_model='EC-Earth3-Veg'

    scenario_record = create_management_actions_records(
        geo_id, result, db)

    return scenario_record

def create_management_actions_records(geo_id, result, db):
    country_code = result['country_code']
    wkt_polygon = result['wkt_polygon']
    climate_models = result['climate_models']
    periods = ','.join(result['periods'])
    sri_species_list = result['sri_species_list']
    logic_type = result['sri_logic_type']
    correction_method = result['sri_correction_method']

    risk_model = result['risk_model']
    risk_type = result['risk_type']

    resilience_dominant_class = result['resilience_dominant_class']
    resilience_polygons = result['resilience_polygons']
    risk_polygons = result['risk_polygons']
    recommendations_polygons = result['recommendations_polygons']
    recommendations_totals = result['recommendations_totals']
    polygons_meta = result['polygons_meta']

    bio_risk_id = result['risk_id']
    xai_humam_text_json = result['xai_humam_text_json']

    new_record = PriorityManagementActionsPolygonsDB(
        id=str(uuid.uuid4()),
        geo_id=geo_id,
        country_code=country_code,
        geometry=wkt_polygon,
        climate_model=str(climate_models),
        risk_type=risk_type,
        risk_model=risk_model,
        sri_species_list=sri_species_list,
        sri_correction_method=correction_method,
        sri_logic_type=logic_type,
        periods=periods,
        resilience_dominant_class=resilience_dominant_class,
        resilience_polygons=resilience_polygons,
        risk_polygons=risk_polygons,
        recommendations_polygons=recommendations_polygons,
        recommendations_totals=recommendations_totals,
        polygons_meta=polygons_meta,
        bio_risk_id=bio_risk_id,
        xai_humam_text_json=xai_humam_text_json
    )

    db.add(new_record)
    db.commit()
    return new_record
