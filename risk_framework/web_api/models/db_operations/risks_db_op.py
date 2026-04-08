import uuid
import pickle
import json
from urllib.parse import urlparse

from sqlalchemy.orm import joinedload

from risk_framework.web_api.models import (
    BiodiversityRiskIndexDB,
    CriticalHabitatIndexDB,
    ProtectedAreaIndexDB,
    SpeciesRichnessIndexDB,
    RasterDataDB,
)
from risk_framework.web_api.schemas import (
    BiodiversityRiskIndexResponse,
    RasterDataResponse,
    RasterSummaryStats,
)
from risk_framework.web_api.utils import (
    get_country_wkt
)

from risk_framework.biodiversity_risk import (
    BioRiskPlusFIS,
    BiofinBiodiversityRiskModelWrapper,
)

from risk_framework.species_models.per_country_species_conf import (
    INDICATOR_SP_PER_COUNTRY,
)


from .sri_db_op import retrieve_or_calculate_sri_future_or_current
from .external_indexes_op import (
    retrieve_or_calculate_ch,
    retrieve_or_calculate_pa,
)


def retrieve_risk_by_id(request, record_id, db):
    query = db.query(BiodiversityRiskIndexDB).options(
        joinedload(BiodiversityRiskIndexDB.green_value_raster),
        joinedload(BiodiversityRiskIndexDB.urban_value_raster),
        joinedload(BiodiversityRiskIndexDB.xai_raster),
    )
    existing_record = query.filter(
        BiodiversityRiskIndexDB.id == record_id
    ).first()

    if not existing_record:
        raise RuntimeError(f"Biodiversity Risk Index record with id {record_id} not found")

    return retrieve_or_calculate_risk(
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        existing_record,
        None,
        None,
        db,
        request
    )


def retrieve_or_calculate_risk_future_or_current(
        country_code,
        wkt_polygon,
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
        future=False,
    ):
    country_code = country_code.upper()
    if not future:
        climate_scenario = 'current'
        period = climate_scenario

    query = db.query(BiodiversityRiskIndexDB).options(
        joinedload(BiodiversityRiskIndexDB.green_value_raster),
        joinedload(BiodiversityRiskIndexDB.urban_value_raster),
        joinedload(BiodiversityRiskIndexDB.xai_raster),
    )
    sri_species_list = sri_override_species_list
    if sri_override_species_list is None:
        sri_species_list = INDICATOR_SP_PER_COUNTRY.get(country_code, INDICATOR_SP_PER_COUNTRY['DEFAULT-EU'])
    sri_species_list.sort()

    sri_species_list_str = ','.join(sri_species_list)
    query = query.filter(
        BiodiversityRiskIndexDB.geo_id == geo_id,
        BiodiversityRiskIndexDB.climate_scenario == climate_scenario,
        BiodiversityRiskIndexDB.sri_logic_type == sri_logic_type,
        BiodiversityRiskIndexDB.sri_correction_method == sri_correction_method,
        BiodiversityRiskIndexDB.sri_species_list == sri_species_list_str,
        BiodiversityRiskIndexDB.crop_to_polygon == crop_to_polygon,
        BiodiversityRiskIndexDB.risk_model == risk_model,
    )
    if future:
        query.filter(
        BiodiversityRiskIndexDB.climate_model == str([climate_model]),
        BiodiversityRiskIndexDB.period == period,
    )

    existing_record = query.first()
    return retrieve_or_calculate_risk(
        country_code,
        wkt_polygon,
        geo_id,
        climate_scenario,
        climate_model,
        period,
        sri_logic_type,
        sri_correction_method,
        sri_override_species_list,
        existing_record,
        crop_to_polygon,
        risk_model,
        db
    )


def retrieve_or_calculate_risk(
        country_code,
        wkt_polygon,
        geo_id,
        climate_scenario,
        climate_model,
        period,
        sri_logic_type,
        sri_correction_method,
        sri_species_list,
        existing_record,
        crop_to_polygon,
        risk_model,
        db,
        request=None
    ):
    # If record exists, retrieve it and return cached result
    if not existing_record:
        existing_record = run_and_create_new_risk_record(
            geo_id,
            country_code.upper(),
            wkt_polygon,
            climate_scenario,
            climate_model,
            period,
            sri_logic_type,
            sri_correction_method,
            sri_species_list,
            crop_to_polygon,
            risk_model,
            db
        )

    existing_green_raster_value = pickle.loads(existing_record.green_value_raster.raster_bin)
    existing_urban_raster_value = pickle.loads(existing_record.urban_value_raster.raster_bin)
    existing_xai_raster_value = pickle.loads(existing_record.xai_raster.raster_bin)

    if request:
        chi_url = urlparse(str(request.url_for("get_chi_record", record_id=existing_record.chi_related_id))).path
        pai_url = urlparse(str(request.url_for("get_pai_record", record_id=existing_record.pai_related_id))).path
        sri_url = urlparse(str(request.url_for("get_sri_record", record_id=existing_record.sri_related_id))).path
    else:
        chi_url=existing_record.chi_related_id
        pai_url=existing_record.pai_related_id
        sri_url=existing_record.sri_related_id

    response = BiodiversityRiskIndexResponse(
        id=existing_record.id,
        country_code=existing_record.country_code,
        geometry=existing_record.geometry,
        scenario=existing_record.climate_scenario,
        climate_model=existing_record.climate_scenario,
        period=existing_record.period,
        crop_to_polygon=existing_record.crop_to_polygon,
        risk_model=existing_record.risk_model,
        xai_summary=existing_record.xai_summary_json,
        risk_ling_thresholds=existing_record.risk_ling_thresholds_json,
        sri_species_list=existing_record.sri_species_list,
        sri_correction_method=existing_record.sri_correction_method,
        sri_logic_type=existing_record.sri_logic_type,
        raster_data=RasterDataResponse(
            raster=existing_green_raster_value,
            summary_stats=RasterSummaryStats(
                mean_raster_value=float(existing_record.green_value_raster.mean_value),
                std_raster_value=float(existing_record.green_value_raster.mean_std)
            ),
            meta=existing_record.green_value_raster.raster_meta
        ),
        raster_data_urban=RasterDataResponse(
            raster=existing_urban_raster_value,
            summary_stats=RasterSummaryStats(
                mean_raster_value=float(existing_record.urban_value_raster.mean_value),
                std_raster_value=float(existing_record.urban_value_raster.mean_std)
            ),
            meta=existing_record.urban_value_raster.raster_meta
        ),
        xai_raster=RasterDataResponse(
            raster=existing_xai_raster_value,
            summary_stats=RasterSummaryStats(
                mean_raster_value=float(existing_record.xai_raster.mean_value),
                std_raster_value=float(existing_record.xai_raster.mean_std)
            ),
            meta=existing_record.xai_raster.raster_meta
        ),
        # chi_id=existing_record.chi_related_id,
        # pai_id=existing_record.pai_related_id,
        # sri_id=existing_record.sri_related_id
        chi=chi_url,
        pai=pai_url,
        sri=sri_url
    )
    return response

def run_and_create_new_risk_record(
        geo_id,
        country_code,
        wkt_polygon,
        climate_scenario,
        climate_model,
        period,
        sri_logic_type,
        sri_correction_method,
        sri_species_list,
        crop_to_polygon,
        risk_model,
        db
    ):
    if wkt_polygon == "" or wkt_polygon is None:
        wkt_polygon = get_country_wkt(country_code)


    ch_retrieval_method = retrieve_or_calculate_ch
    pa_retrieval_method = retrieve_or_calculate_pa
    sri_retrieval_method = retrieve_or_calculate_sri_future_or_current
    risk_model = BiofinBiodiversityRiskModelWrapper(
        geo_id,
        country_code,
        wkt_polygon,
        ch_retrieval_method, pa_retrieval_method, sri_retrieval_method,
        sri_logic_type, sri_correction_method, sri_species_list,
        crop_to_polygon=crop_to_polygon, risk_model=risk_model, db=db
    )

    result = risk_model.run(climate_scenario=climate_scenario, climate_model=climate_model, period=period)

    scenario_record = create_risk_and_raster_records(
        geo_id, result, db)

    return scenario_record

def create_risk_and_raster_records(geo_id, result, db):

    country_code = result['country_code']
    wkt_polygon = result['wkt_polygon']
    climate_scenario = result['climate_scenario']
    climate_models = result['climate_models']
    period = result['period']
    sri_species_list = result['sri_species_list']
    logic_type = result['sri_logic_type']
    correction_method = result['sri_correction_method']

    xai_data = result['xai_data']
    xai_summary = xai_data['xai_summary_json']
    risk_model = result['risk_model']
    crop_to_polygon = result['crop_to_polygon']
    risk_ling_thresholds = result['risk_ling_thresholds']


    chi_reg_id = result['meta']['ch_reg_id']
    pai_reg_id = result['meta']['pa_reg_id']
    sri_reg_id = result['meta']['sri_reg_id']

    if climate_scenario == 'current':
        climate_models = ''
    green_raster_data = result['green_raster_data']
    green_raster_values = green_raster_data['raster']
    raster_meta = green_raster_data['meta']
    raster_meta['crs'] = str(raster_meta['crs'])
    green_raster_summary = green_raster_data['summary_stats']
    green_mean_value = green_raster_summary['mean_raster_value']
    green_mean_std = green_raster_summary['std_raster_value']

    new_green_raster_data = create_raster_record(geo_id, green_raster_values, raster_meta, green_mean_value, green_mean_std)
    db.add(new_green_raster_data)
    db.flush()

    urban_raster_data = result['urban_raster_data']
    urban_raster_values = urban_raster_data['raster']
    urban_raster_summary = urban_raster_data['summary_stats']
    urban_mean_value = urban_raster_summary['mean_raster_value']
    urban_mean_std = urban_raster_summary['std_raster_value']


    new_urban_raster_data = create_raster_record(geo_id, urban_raster_values, raster_meta, urban_mean_value, urban_mean_std)
    db.add(new_urban_raster_data)
    db.flush()

    xai_raster_values = xai_data['xai_raster']
    xai_raster_meta = raster_meta
    # replace with none:
    xai_mean_value = -1
    xai_mean_std = -1
    new_xai_raster_data = create_raster_record(geo_id, xai_raster_values, xai_raster_meta, xai_mean_value, xai_mean_std)
    db.add(new_xai_raster_data)
    db.flush()


    new_record = BiodiversityRiskIndexDB(
        id=str(uuid.uuid4()),
        geo_id=geo_id,
        country_code=country_code,
        geometry=wkt_polygon,
        green_value_raster_id=new_green_raster_data.id,
        urban_value_raster_id=new_urban_raster_data.id,
        xai_raster_id=new_xai_raster_data.id,
        xai_summary_json=xai_summary,
        risk_model=risk_model,
        risk_ling_thresholds_json=risk_ling_thresholds,
        crop_to_polygon=crop_to_polygon,
        climate_scenario=climate_scenario,
        climate_model=str(climate_models),
        period=period,
        sri_species_list=sri_species_list,
        sri_correction_method=correction_method,
        sri_logic_type=logic_type,
        chi_related_id=chi_reg_id,
        pai_related_id=pai_reg_id,
        sri_related_id=sri_reg_id,
    )

    db.add(new_record)
    db.commit()
    new_record.green_value_raster = new_green_raster_data
    new_record.urban_value_raster = new_urban_raster_data
    new_record.xai_raster = new_xai_raster_data
    return new_record


def create_raster_record(geo_id, raster_values, raster_meta, mean_value, mean_std):
    new_raster_data = RasterDataDB(
        id=str(uuid.uuid4()),
        geo_id=geo_id,
        raster_bin=pickle.dumps(raster_values),
        raster_meta=raster_meta,
        mean_value=float(mean_value),
        mean_std=float(mean_std),
    )
    return new_raster_data
