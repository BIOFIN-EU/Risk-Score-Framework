import uuid
import pickle

from sqlalchemy.orm import joinedload

from risk_framework.web_api.models import (
    SpeciesHabitatSuitabilityIndexDB,
    SpeciesRichnessIndexDB,
    RasterDataDB,
)
from risk_framework.web_api.schemas import (
    SpeciesHabitatSuitabilityIndexResponse,
    SpeciesRichnessIndexResponse,
    RasterDataResponse,
    RasterSummaryStats,
)
from risk_framework.web_api.utils import (
    get_country_wkt
)
from risk_framework.species_models.base import (
    SpeciesHabitatSuitabilityModel
)

from risk_framework.species_models.sri_model import (
    FuzzySRIModel
)

from risk_framework.species_models.per_country_species_conf import (
    INDICATOR_SP_PER_COUNTRY,
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
        species_list = INDICATOR_SP_PER_COUNTRY.get(country_code, [])

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

    existing_hsi_record = query.first()
    return retrieve_or_calculate_sri(species_list, country_code, wkt_polygon, geo_id, climate_scenario, climate_model, period, logic_type, correction_method, existing_hsi_record, db)


def retrieve_or_calculate_sri(species_list, country_code, wkt_polygon, geo_id, climate_scenario, climate_model, period, logic_type, correction_method, existing_record, db):
    # If record exists, retrieve it and return cached result
    if not existing_record:
        existing_record = run_and_create_new_sri_record(species_list, geo_id, country_code.upper(), climate_scenario, climate_model, period, logic_type, correction_method, wkt_polygon, db)

    existing_raster_value = pickle.loads(existing_record.value_raster.raster_bin)

    return SpeciesRichnessIndexResponse(
        id=existing_record.id,
        species_list=existing_record.species_list,
        country_code=existing_record.country_code,
        wkt_polygon=existing_record.wkt_polygon,
        scenario=existing_record.climate_scenario,
        climate_model=existing_record.climate_scenario,
        period=existing_record.period,
        correction_method=existing_record.correction_method,
        logic_type=existing_record.logic_type,
        raster_data=RasterDataResponse(
            raster=existing_raster_value,
            summary_stats=RasterSummaryStats(
                mean_habitat_suitability=float(existing_record.value_raster.mean_value),
                std_habitat_suitability=float(existing_record.value_raster.mean_std)
            ),
            meta=existing_record.value_raster.raster_meta
        )
    )

def run_and_create_new_sri_record(species_list, geo_id, country_code, wkt_polygon, climate_scenario, climate_model, period, logic_type, correction_method, db):
    if wkt_polygon == "" or wkt_polygon is None:
        wkt_polygon = get_country_wkt(country_code)

    if logic_type.lower() == 'fuzzy':
        sri_model = FuzzySRIModel(correction_method, country_code, wkt_polygon=wkt_polygon, db=db, species_list=species_list)
    else:
        sri_model = FuzzySRIModel(correction_method, country_code, wkt_polygon=wkt_polygon, db=db, species_list=species_list)

    result = sri_model.run(climate_scenario=climate_scenario, climate_model=climate_model, period=period)

    scenario_record = create_sri_and_raster_records(
        geo_id, result, db)

    return {
        'scenarios': {
            climate_scenario: {
                'periods': {
                    period: scenario_record
                }
            }
        }
    }

def create_sri_and_raster_records(geo_id, result, db):
    species_list = ','.join(result['species_list'])
    country_code = result['country_code']
    wkt_polygon = result['wkt_polygon']
    climate_scenario = result['climate_scenario']
    climate_models = result['climate_models']
    period = result['period']

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
        period=period
    )

    db.add(new_record)
    db.commit()
    new_record.value_raster = new_raster_data
    return new_record


def retrieve_or_calculate_hsi_future_or_current(species_name, country_code, wkt_polygon, geo_id, climate_scenario, climate_model, period, db, future=False):
    country_code = country_code.upper()
    if not future:
        climate_scenario = 'current'
        period = climate_scenario

    query = db.query(SpeciesHabitatSuitabilityIndexDB).options(
        joinedload(SpeciesHabitatSuitabilityIndexDB.value_raster)
    )

    query = query.filter(
        SpeciesHabitatSuitabilityIndexDB.geo_id == geo_id,
        SpeciesHabitatSuitabilityIndexDB.species == species_name,
        SpeciesHabitatSuitabilityIndexDB.climate_scenario == climate_scenario,
    )
    if future:
        query.filter(
        SpeciesHabitatSuitabilityIndexDB.climate_model == str([climate_model]),
        SpeciesHabitatSuitabilityIndexDB.period == period,
    )

    existing_hsi_record = query.first()
    return retrieve_or_calculate_hsi(species_name, country_code, wkt_polygon, geo_id, climate_scenario, period, existing_hsi_record, db)



def retrieve_or_calculate_hsi(species_name, country_code, wkt_polygon, geo_id, climate_scenario, period, existing_hsi_record, db):
    # If record exists, retrieve it and return cached result
    if not existing_hsi_record:
        existing_hsi_dict = run_and_create_new_hsi_records(
            geo_id, species_name, country_code.upper(), wkt_polygon, db)
        existing_hsi_record = existing_hsi_dict['scenarios'][climate_scenario]['periods'][period]

    existing_raster_value = pickle.loads(existing_hsi_record.value_raster.raster_bin)



    return SpeciesHabitatSuitabilityIndexResponse(
        id=existing_hsi_record.id,
        species=existing_hsi_record.species,
        country_code=existing_hsi_record.country_code,
        wkt_polygon=existing_hsi_record.wkt_polygon,
        climate_scenario=existing_hsi_record.climate_scenario,
        climate_model=existing_hsi_record.climate_model,
        period=existing_hsi_record.period,
        raster_data=RasterDataResponse(
            raster=existing_raster_value,
            summary_stats=RasterSummaryStats(
                mean_habitat_suitability=float(existing_hsi_record.value_raster.mean_value),
                std_habitat_suitability=float(existing_hsi_record.value_raster.mean_std)
            ),
            meta=existing_hsi_record.value_raster.raster_meta
        )
    )

def run_and_create_new_hsi_records(geo_id, species_name, country_code, wkt_polygon, db):
    country_code = country_code.upper()
    if wkt_polygon == "" or wkt_polygon is None:
        wkt_polygon = get_country_wkt(country_code)

    run_extra_confs = {
        'SPECIES_SCIENTIFIC_NAME': species_name,
        'COUNTRY_CODE': country_code,
        'WKT_POLYGON': wkt_polygon,
    }

    hsi_model = SpeciesHabitatSuitabilityModel(run_extra_confs)

    all_results = hsi_model.run(run_extra_confs)

    # Extract first scenario and period
    scenarios_records = {}
    for scenario, periods_dict in all_results['scenarios'].items():
        scenarios_records[scenario] = {
            'periods': {}
        }
        for period, result in periods_dict['periods'].items():
            raster_values = result['raster']
            raster_summary = result['summary_stats']
            raster_meta = result['meta']
            raster_meta['nodata'] = -1
            scenario_record = create_hsi_and_raster_records(
                geo_id, all_results, scenario, period, wkt_polygon, raster_values, raster_summary, raster_meta, db)
            scenarios_records[scenario]['periods'][period] = scenario_record
    return {'scenarios': scenarios_records}

def create_hsi_and_raster_records(geo_id, all_results, scenario, period, wkt_polygon, raster_values, raster_summary, raster_meta, db):
    species_name = all_results['species']
    country_code = all_results['country']
    climate_models = all_results['climate_models']
    if scenario == 'current':
        climate_models = ''
    mean_value = raster_summary['mean_habitat_suitability']
    mean_std = raster_summary['std_habitat_suitability']
    new_raster_data = RasterDataDB(
        id=str(uuid.uuid4()),
        geo_id=geo_id,
        raster_bin=pickle.dumps(raster_values),
        raster_meta=raster_meta,
        mean_value=float(mean_value),
        mean_std=float(mean_std)
    )

    db.add(new_raster_data)
    db.flush()

    new_record = SpeciesHabitatSuitabilityIndexDB(
        id=str(uuid.uuid4()),
        geo_id=geo_id,  # Deterministic geo_id for lookup
        value_raster_id=new_raster_data.id,
        geometry=wkt_polygon,
        species=species_name,
        country_code=country_code,
        climate_scenario=scenario,
        climate_model=str(climate_models),  # Extract from your model results if available
        period=period
    )

    db.add(new_record)
    db.commit()
    new_record.value_raster = new_raster_data
    return new_record
