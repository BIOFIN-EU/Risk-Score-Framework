import uuid
import pickle

from sqlalchemy.orm import joinedload

from risk_framework.web_api.models import (
    SpeciesHabitatSuitabilityIndexDB,
    RasterData,
)
from risk_framework.web_api.schemas import (
    SpeciesHabitatSuitabilityIndexResponse,
    RasterDataResponse,
    RasterSummaryStats,
)
from risk_framework.web_api.utils import (
    get_country_wkt
)
from risk_framework.species_models.base import SpeciesHabitatSuitabilityModel


def create_hsi_and_raster_records(geo_id, all_results, scenario, period, wkt_polygon, raster_values, raster_summary, raster_meta, db):
    species_name = all_results['species']
    country_code = all_results['country']
    climate_models = all_results['climate_models']
    if scenario == 'current':
        climate_models = ''
    mean_value = raster_summary['mean_habitat_suitability']
    mean_std = raster_summary['std_habitat_suitability']
    new_raster_data = RasterData(
        id=str(uuid.uuid4()),
        geo_id=geo_id,
        raster_bin=pickle.dumps(raster_values),
        raster_meta=raster_meta
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
        period=period,
        mean_value=float(mean_value),
        mean_std=float(mean_std),
    )

    db.add(new_record)
    db.commit()
    new_record.value_raster = new_raster_data
    return new_record


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
        country=existing_hsi_record.country_code,
        scenario=existing_hsi_record.climate_scenario,
        period=existing_hsi_record.period,
        raster_data=RasterDataResponse(
            raster=existing_raster_value,
            summary_stats=RasterSummaryStats(
                mean_habitat_suitability=float(existing_hsi_record.mean_value),
                std_habitat_suitability=float(existing_hsi_record.mean_std)
            )
        ),
        meta=existing_hsi_record.value_raster.raster_meta
    )
