import pickle
import json
import uuid
from typing import Optional

from sqlalchemy.orm import Session, joinedload
from fastapi import FastAPI, HTTPException, APIRouter, Depends

# from risk_framework.web_api.core import app
from risk_framework.web_api.models import (
    SpeciesHabitatSuitabilityIndexDB,
    RasterData,
)
from risk_framework.web_api.schemas import (
    FutureSpeciesHabitatSuitabilityIndexRequest,
    CurrentSpeciesHabitatSuitabilityIndexRequest,
    SpeciesHabitatSuitabilityIndexResponse,
    RasterDataResponse,
    RasterSummaryStats,
)
from risk_framework.web_api.utils import (
    get_db,
    generate_geo_uuid
)
from risk_framework.species_models.base import SpeciesHabitatSuitabilityModel



hsi_router = APIRouter()



def create_hsi_and_raster_records(geo_id, all_results, scenario, period, wkt_poligon, raster_values, raster_summary, raster_meta, db):
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
        geometry=wkt_poligon,
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


def run_and_create_new_hsi_records(geo_id, species_name, country_code, wkt_poligon, db):
    run_extra_confs = {
        'SPECIES_SCIENTIFIC_NAME': species_name,
        'COUNTRY_CODE': country_code.upper()
    }
    if wkt_poligon:
        run_extra_confs['WKT_POLIGON'] = wkt_poligon
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
            raster_summary = result['summary_stats']
            scenario_record = create_hsi_and_raster_records(
                geo_id, all_results, scenario, period, wkt_poligon, raster_values, raster_summary, all_results['meta'], db)
            scenarios_records[scenario]['periods'][period] = scenario_record
    return {'scenarios': scenarios_records}


def retrieve_or_calculate_hsi(request, geo_id, climate_scenario, period, existing_hsi_record, db):
    # If record exists, retrieve it and return cached result
    if not existing_hsi_record:
        existing_hsi_dict = run_and_create_new_hsi_records(
            geo_id, request.species_name, request.country_code.upper(), request.wkt_poligon, db)
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


@hsi_router.post("/predict-future-habitat-suitability/", response_model=SpeciesHabitatSuitabilityIndexResponse)
async def predict_future_species_habitat_suitability_index(request: FutureSpeciesHabitatSuitabilityIndexRequest, db: Session = Depends(get_db)):
    """
    Predict future species habitat suitability index based on species name, country code, climate scenario, model and period
    and optional WKT polygon.

    Parameters:
    - **species_name**: Scientific name of the species
    - **country_code**: ISO country code
    - **wkt_poligon**: Optional WKT (Well-Known Text) polygon string
    - **climate_scenario**: climate scenario string
    - **climate_model**: climate model string
    - **period**: period (eg: 2021-2040) string
    Returns:
    - JSON dictionary containing the species habitat suitability index results
    """
    try:
        geo_id = generate_geo_uuid(
            request.species_name,
            request.country_code,
            request.wkt_poligon
        )
        query = db.query(SpeciesHabitatSuitabilityIndexDB).options(
            joinedload(SpeciesHabitatSuitabilityIndexDB.value_raster)
        )
        query = query.filter(
            SpeciesHabitatSuitabilityIndexDB.geo_id == geo_id,
            SpeciesHabitatSuitabilityIndexDB.climate_scenario == request.climate_scenario,
            SpeciesHabitatSuitabilityIndexDB.climate_model == str([request.climate_model]),
            SpeciesHabitatSuitabilityIndexDB.period == request.period,
        )

        existing_hsi_record = query.first()
        return retrieve_or_calculate_hsi(request, geo_id, request.climate_scenario, request.period, existing_hsi_record, db)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@hsi_router.post("/calculate-current-habitat-suitability/", response_model=SpeciesHabitatSuitabilityIndexResponse)
async def calculate_current_species_habitat_suitability_index(request: CurrentSpeciesHabitatSuitabilityIndexRequest, db: Session = Depends(get_db)):
    """
    Calculate current species habitat suitability index based on species name, country code,
    and optional WKT polygon.

    Parameters:
    - **species_name**: Scientific name of the species
    - **country_code**: ISO country code
    - **wkt_poligon**: Optional WKT (Well-Known Text) polygon string
    Returns:
    - JSON dictionary containing the species habitat suitability index results
    """
    climate_scenario = 'current'
    period = climate_scenario
    # try:
    geo_id = generate_geo_uuid(
        request.species_name,
        request.country_code,
        request.wkt_poligon
    )
    query = db.query(SpeciesHabitatSuitabilityIndexDB).options(
        joinedload(SpeciesHabitatSuitabilityIndexDB.value_raster)
    )
    query = query.filter(
        SpeciesHabitatSuitabilityIndexDB.geo_id == geo_id,
        SpeciesHabitatSuitabilityIndexDB.climate_scenario == climate_scenario,
    )

    existing_hsi_record = query.first()
    return retrieve_or_calculate_hsi(request, geo_id, climate_scenario, period, existing_hsi_record, db)
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

