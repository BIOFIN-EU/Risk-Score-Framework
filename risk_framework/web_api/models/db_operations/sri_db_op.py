import uuid
import pickle

from sqlalchemy.orm import joinedload

from risk_framework.web_api.models import (
    SpeciesHabitatSuitabilityIndexDB,
    SpeciesRichnessIndexDB,
    RasterDataDB,
)
from risk_framework.web_api.schemas import (
    SpeciesRichnessIndexResponse,
    RasterDataResponse,
    RasterSummaryStats,
)
from risk_framework.web_api.utils import (
    get_country_wkt
)
from risk_framework.species_models.sri_model import (
    FuzzySRIModel
)

from risk_framework.species_models.per_country_species_conf import (
    INDICATOR_SP_PER_COUNTRY,
)

from .hsi_db_op import retrieve_or_calculate_hsi_future_or_current


def retrieve_sri_by_id(record_id, db):
    query = db.query(SpeciesRichnessIndexDB).options(
        joinedload(SpeciesRichnessIndexDB.value_raster)
    )
    existing_record = query.filter(
        SpeciesRichnessIndexDB.id == record_id
    ).first()

    if not existing_record:
        raise RuntimeError(f"Species Richness Index  record with id {record_id} not found")

    return retrieve_or_calculate_sri(
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
        db
    )


def retrieve_or_calculate_sri_future_or_current(override_species_list, country_code, wkt_polygon, geo_id, climate_scenario, climate_model, period, logic_type, correction_method, db, future=False):
    country_code = country_code.upper()
    if not future:
        climate_scenario = 'current'
        period = climate_scenario

    query = db.query(SpeciesRichnessIndexDB).options(
        joinedload(SpeciesRichnessIndexDB.value_raster)
    )
    species_list = override_species_list
    if override_species_list is None:
        species_list = INDICATOR_SP_PER_COUNTRY.get(country_code, INDICATOR_SP_PER_COUNTRY['DEFAULT-EU'])

    species_list.sort()

    species_list_str = ','.join(species_list)
    query = query.filter(
        SpeciesRichnessIndexDB.geo_id == geo_id,
        SpeciesRichnessIndexDB.climate_scenario == climate_scenario,
        SpeciesRichnessIndexDB.logic_type == logic_type,
        SpeciesRichnessIndexDB.correction_method == correction_method,
        SpeciesRichnessIndexDB.species_list == species_list_str,
    )
    if future:
        query.filter(
        SpeciesRichnessIndexDB.climate_model == str([climate_model]),
        SpeciesRichnessIndexDB.period == period,
    )

    existing_record = query.first()
    return retrieve_or_calculate_sri(species_list, country_code, wkt_polygon, geo_id, climate_scenario, climate_model, period, logic_type, correction_method, existing_record, db)


def retrieve_or_calculate_sri(species_list, country_code, wkt_polygon, geo_id, climate_scenario, climate_model, period, logic_type, correction_method, existing_record, db):
    # If record exists, retrieve it and return cached result
    if not existing_record:
        existing_record = run_and_create_new_sri_record(
            species_list,
            geo_id,
            country_code.upper(),
            wkt_polygon,
            climate_scenario,
            climate_model,
            period,
            logic_type,
            correction_method,
            db
        )

    existing_raster_value = pickle.loads(existing_record.value_raster.raster_bin)

    return SpeciesRichnessIndexResponse(
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

def run_and_create_new_sri_record(species_list, geo_id, country_code, wkt_polygon, climate_scenario, climate_model, period, logic_type, correction_method, db):
    if wkt_polygon == "" or wkt_polygon is None:
        wkt_polygon = get_country_wkt(country_code)

    hsi_retrieval_method = retrieve_or_calculate_hsi_future_or_current
    if logic_type.lower() == 'fuzzy':
        sri_model = FuzzySRIModel(geo_id, hsi_retrieval_method, correction_method, country_code, wkt_polygon=wkt_polygon, db=db, species_list=species_list)
    else:
        sri_model = FuzzySRIModel(geo_id, hsi_retrieval_method, correction_method, country_code, wkt_polygon=wkt_polygon, db=db, species_list=species_list)

    result = sri_model.run(climate_scenario=climate_scenario, climate_model=climate_model, period=period)

    scenario_record = create_sri_and_raster_records(
        geo_id, result, db)

    return scenario_record

def create_sri_and_raster_records(geo_id, result, db):
    species_list = ','.join(result['species_list'])
    country_code = result['country_code']
    wkt_polygon = result['wkt_polygon']
    climate_scenario = result['climate_scenario']
    climate_models = result['climate_models']
    period = result['period']
    correction_method = result['correction_method']
    logic_type = result['logic_type']
    # hsi_registry_list = result['meta']['hsi_registry_list']

    hsi_id_list = result['meta']['hsi_id_list']

    hsi_instances = db.query(SpeciesHabitatSuitabilityIndexDB).filter(
        SpeciesHabitatSuitabilityIndexDB.id.in_(hsi_id_list)
    ).all()

    if climate_scenario == 'current':
        climate_models = ''
    raster_data = result['raster_data']
    raster_values = raster_data['raster']
    raster_meta = raster_data['meta']
    raster_summary = raster_data['summary_stats']
    mean_value = raster_summary['mean_raster_value']
    mean_std = raster_summary['std_raster_value']

    new_raster_data = RasterDataDB(
        id=str(uuid.uuid4()),
        geo_id=geo_id,
        raster_bin=pickle.dumps(raster_values),
        raster_meta=raster_meta,
        mean_value=float(mean_value),
        mean_std=float(mean_std),
    )

    db.add(new_raster_data)
    db.flush()

    new_record = SpeciesRichnessIndexDB(
        id=str(uuid.uuid4()),
        geo_id=geo_id,
        value_raster_id=new_raster_data.id,
        geometry=wkt_polygon,
        species_list=species_list,
        country_code=country_code,
        climate_scenario=climate_scenario,
        climate_model=str(climate_models),
        period=period,
        correction_method=correction_method,
        logic_type=logic_type,
        # hsi_related=hsi_registry_list
        hsi_related=hsi_instances
    )

    db.add(new_record)
    db.commit()
    new_record.value_raster = new_raster_data
    return new_record

