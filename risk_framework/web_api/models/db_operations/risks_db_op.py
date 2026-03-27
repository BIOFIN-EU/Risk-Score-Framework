import uuid
import pickle

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
        joinedload(BiodiversityRiskIndexDB.value_raster)
    )
    sri_species_list = sri_override_species_list
    if sri_override_species_list is None:
        sri_species_list = INDICATOR_SP_PER_COUNTRY.get(country_code, [])

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

    existing_hsi_record = query.first()
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
        existing_hsi_record,
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
        db
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

    existing_raster_value = pickle.loads(existing_record.value_raster.raster_bin)

    return BiodiversityRiskIndexResponse(
        id=existing_record.id,
        species_list=existing_record.species_list,
        country_code=existing_record.country_code,
        geometry=existing_record.geometry,
        scenario=existing_record.climate_scenario,
        climate_model=existing_record.climate_scenario,
        period=existing_record.period,
        correction_method=existing_record.correction_method,
        logic_type=existing_record.logic_type,
        raster_data=RasterDataResponse(
            raster=existing_raster_value,
            summary_stats=RasterSummaryStats(
                mean_raster_value=float(existing_record.value_raster.mean_value),
                std_raster_value=float(existing_record.value_raster.mean_std)
            ),
            meta=existing_record.value_raster.raster_meta
        )
    )

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


    ch_retrieval_method = retrieve_or_calculate_ch,
    pa_retrieval_method = retrieve_or_calculate_pa,
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
    sri_species_list = ','.join(result['species_list'])
    country_code = result['country_code']
    wkt_polygon = result['wkt_polygon']
    climate_scenario = result['climate_scenario']
    climate_models = result['climate_models']
    period = result['period']
    correction_method = result['correction_method']
    logic_type = result['logic_type']

    xai_summary = result['xai_summary']
    risk_model = result['risk_model']
    crop_to_polygon = result['crop_to_polygon']
    risk_ling_thresholds = result['risk_ling_thresholds']

    chi_id_list = result['meta']['chi_id_list']
    pai_id_list = result['meta']['pai_id_list']
    sri_id_list = result['meta']['sri_id_list']

    chi_instances = db.query(CriticalHabitatIndexDB).filter(
        CriticalHabitatIndexDB.id.in_(chi_id_list)
    ).all()
    pai_instances = db.query(ProtectedAreaIndexDB).filter(
        ProtectedAreaIndexDB.id.in_(pai_id_list)
    ).all()
    sri_instances = db.query(SpeciesRichnessIndexDB).filter(
        SpeciesRichnessIndexDB.id.in_(sri_id_list)
    ).all()

    if climate_scenario == 'current':
        climate_models = ''
    raster_data = result['raster_data']
    raster_values = raster_data['raster']
    raster_meta = raster_data['meta']
    raster_summary = raster_data['summary_stats']
    mean_value = raster_summary['mean_raster_value']
    mean_std = raster_summary['std_raster_value']

    new_raster_data = create_raster_record(geo_id, raster_values, raster_meta, mean_value, mean_std)
    db.add(new_raster_data)
    db.flush()

    xai_raster_data = result['xai_raster_data']
    xai_raster_values = xai_raster_data['raster']
    xai_raster_meta = xai_raster_data['meta']
    xai_raster_summary = xai_raster_data['summary_stats']
    xai_mean_value = xai_raster_summary['mean_raster_value']
    xai_mean_std = xai_raster_summary['std_raster_value']
    new_xai_raster_data = create_raster_record(geo_id, xai_raster_values, xai_raster_meta, xai_mean_value, xai_mean_std)
    db.add(new_xai_raster_data)
    db.flush()


    new_record = BiodiversityRiskIndexDB(
        id=str(uuid.uuid4()),
        geo_id=geo_id,
        country_code=country_code,
        geometry=wkt_polygon,
        value_raster_id=new_raster_data.id,
        xai_raster_id=new_xai_raster_data.id,
        xai_summary_json=xai_summary,
        risk_model=risk_model,
        risk_ling_thresholds=risk_ling_thresholds,
        crop_to_polygon=crop_to_polygon,
        climate_scenario=climate_scenario,
        climate_model=str(climate_models),
        period=period,
        sri_species_list=sri_species_list,
        sri_correction_method=correction_method,
        sri_logic_type=logic_type,
        chi_related=chi_instances,
        pai_related=pai_instances,
        sri_related=sri_instances,
    )


    db.add(new_record)
    db.commit()
    new_record.value_raster = new_raster_data
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
