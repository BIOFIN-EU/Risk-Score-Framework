import hashlib
import json
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import FastAPI, HTTPException, APIRouter, Depends
from risk_framework.web_api.models import (
    SpeciesRichnessSuitabilityIndexDB,
    RasterData,
)
from risk_framework.web_api.schemas import (
    SpeciesRichnessSuitabilityIndexRequest,
    SpeciesRichnessSuitabilityIndexResponse,
    RasterDataResponse,
    RasterSummaryStats,
)
from risk_framework.species_models.base import SpeciesSuitabilityModel
from risk_framework.conf import SessionLocal

# Create FastAPI instance
app = FastAPI(
    title="Risk Framework API",
    description="API for biodiversity risk assessment",
    version="0.1.0",
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_geo_uuid(species_name: str, country_code: str, wkt_polygon: Optional[str] = None) -> str:
    """
    Generate a deterministic UUID based on input parameters.
    Uses empty string for optional wkt_polygon if not provided.
    """
    # Use empty string if wkt_polygon is None
    polygon_str = wkt_polygon if wkt_polygon else ""

    # Create a string combining all parameters
    input_string = f"{species_name}_{country_code}_{polygon_str}"

    # Generate a UUID from the hash of the input string
    # UUID v5 uses a namespace and name to generate consistent UUIDs
    namespace = uuid.NAMESPACE_DNS  # You can use any fixed namespace
    cache_uuid = str(uuid.uuid5(namespace, input_string))

    return cache_uuid


router = APIRouter()

@app.get("/")
async def hello_world():
    """
    Hello World endpoint.

    Returns a simple greeting message.
    """
    return {"message": "Hello World"}



async def run_and_creat_new_ssri_record(geo_id, species_name, country_code, wkt_poligon, db):
    # If no record exists, run the model
    ssi_model = SpeciesSuitabilityModel({
        'SPECIES_SCIENTIFIC_NAME': species_name,
        'COUNTRY_CODE': country_code.upper()
    })

    run_extra_confs = {}
    if wkt_poligon:
        run_extra_confs['WKT_POLIGON'] = wkt_poligon

    result = ssi_model.run(run_extra_confs)

    # Extract first scenario and period
    first_scenario = next(iter(result['scenarios']))
    first_period = next(iter(result['scenarios'][first_scenario]['periods']))
    period_data = result['scenarios'][first_scenario]['periods'][first_period]

    # Prepare raster data for storage
    raster_values = period_data['raster']

    # Create RasterData record
    new_raster_data = RasterData(
        id=str(uuid.uuid4()),
        geo_id=uuid.uuid4(),
        raster_bin=json.dumps(raster_values).encode('utf-8'),
        raster_meta=result['meta']
    )

    db.add(new_raster_data)
    db.flush()

    # Create new SpeciesRichnessSuitabilityIndexDB record with deterministic geo_id
    new_record = SpeciesRichnessSuitabilityIndexDB(
        id=str(uuid.uuid4()),  # Random id for primary key
        geo_id=geo_id,  # Deterministic geo_id for lookup
        value_raster_id=new_raster_data.id,
        # explainability_raster_id=new_raster_data.id,  # Using same raster for explainability
        species=result['species'],
        country_code=result['country'],
        climate_scenario=first_scenario,
        climate_model="unknown",  # Extract from your model results if available
        period=first_period,
        has_humam_footprint=False,  # Set based on your model logic
        mean_value=float(period_data['summary_stats']['mean_habitat_suitability']),
        mean_std=float(period_data['summary_stats']['std_habitat_suitability']),
    )

    db.add(new_record)
    db.flush()
    return new_record, new_raster_data

@router.post("/species-richness-index/", response_model=SpeciesRichnessSuitabilityIndexResponse)
async def calculate_species_richness_index(request: SpeciesRichnessSuitabilityIndexRequest , db: Session = Depends(get_db)):
    """
    Calculate species richness index based on species name, country code,
    and optional WKT polygon.

    Parameters:
    - **species_name**: Scientific name of the species
    - **country_code**: ISO country code
    - **wkt_poligon**: Optional WKT (Well-Known Text) polygon string

    Returns:
    - JSON dictionary containing the species richness index results
    """
    try:
        geo_id = generate_geo_uuid(
            request.species_name,
            request.country_code,
            request.wkt_poligon
        )
        existing_srsi = db.query(SpeciesRichnessSuitabilityIndexDB).filter(
            SpeciesRichnessSuitabilityIndexDB.geo_id == geo_id
        ).first()
        existing_raster = None
        # If record exists, retrieve it and return cached result
        if existing_srsi:
            # Get the associated raster data
            existing_raster = db.query(RasterData).filter(
                RasterData.id == existing_srsi.value_raster_id
            ).first()

            if not existing_raster:
                raise HTTPException(status_code=500, detail="Cached raster data not found")

            # Parse the raster binary back to list of lists
        else:
            existing_record, existing_raster = run_and_creat_new_ssri_record(
                geo_id, request.species_name, request.country_code.upper(), request.wkt_poligon, db)

        existing_raster_value = json.loads(existing_raster.raster_bin.decode('utf-8'))
        return SpeciesRichnessSuitabilityIndexResponse(
            id=existing_record.id,
            species=existing_record.species,
            country=existing_record.country_code,
            scenario=existing_record.climate_scenario,
            period=existing_record.period,
            raster_data=RasterDataResponse(
                raster=existing_raster_value,
                summary_stats=RasterSummaryStats(
                    mean_habitat_suitability=float(existing_record.mean_value),
                    std_habitat_suitability=float(existing_record.mean_std)
                )
            ),
            meta=existing_raster.raster_meta
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

app.include_router(router, prefix="/api/v1")  # All router endpoints will be under /api/v1
