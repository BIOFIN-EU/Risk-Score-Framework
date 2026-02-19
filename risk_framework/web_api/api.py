from fastapi import FastAPI, HTTPException

from risk_framework.web_api.schemas import (
    SpeciesRichnessSuitabilityIndexRequest,
    SpeciesRichnessSuitabilityIndex,
)
from risk_framework.species_models.base import SpeciesSuitabilityModel

# Create FastAPI instance
app = FastAPI(
    title="Risk Framework API",
    description="API for biodiversity risk assessment",
    version="0.1.0",
)

@app.get("/")
async def hello_world():
    """
    Hello World endpoint.

    Returns a simple greeting message.
    """
    return {"message": "Hello World"}


@app.post("/species-richness-index/")
async def calculate_species_richness_index(request: SpeciesRichnessSuitabilityIndexRequest):
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
        ssi_model = SpeciesSuitabilityModel({
            'SPECIES_SCIENTIFIC_NAME': request.species_name,
            'COUNTRY_CODE': request.country_code.upper()
        })

        run_extra_confs = {}
        if request.wkt_poligon:
            run_extra_confs['WKT_POLIGON'] = request.wkt_poligon

        result = ssi_model.run(run_extra_confs)
        # # Convert your result to match SpeciesSuitabilityIndex schema
        # return SpeciesRichnessSuitabilityIndex(
        #     id=result.get('id', ''),
        #     geo_id=result.get('geo_id'),
        #     value_raster_id=result.get('value_raster_id', ''),
        #     explainability_raster_id=result.get('explainability_raster_id', ''),
        #     species=request.species_name,
        #     country_code=request.country_code,
        #     climate_scenario=result.get('climate_scenario', ''),
        #     climate_model=result.get('climate_model', ''),
        #     period=result.get('period', ''),
        #     has_humam_footprint=result.get('has_human_footprint', False),
        #     mean_value=result.get('mean_value', 0),
        #     mean_std=result.get('mean_std', 0),
        #     mean_explainability=result.get('mean_explainability', {})
        # )

        # return {'a'}  # FastAPI will auto-convert dict to JSON
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
