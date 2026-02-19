from fastapi import FastAPI, HTTPException

from risk_framework.web_api.schemas import (
    SpeciesRichnessSuitabilityIndexRequest,
    SpeciesRichnessSuitabilityIndex,
    RasterDataResponse,
    RasterSummaryStats,
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


@app.post("/species-richness-index/", response_model=SpeciesRichnessSuitabilityIndex)
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
        first_scenario = next(iter(result['scenarios']))
        first_period = next(iter(result['scenarios'][first_scenario]['periods']))

        period_data = result['scenarios'][first_scenario]['periods'][first_period]
        import ipdb; ipdb.set_trace()

        return SpeciesRichnessSuitabilityIndex(
            species=result['species'],
            country=result['country'],
            scenario=first_scenario,
            period=first_period,
            raster_data=RasterDataResponse(
                raster=period_data['raster'],
                summary_stats=RasterSummaryStats(
                    mean_habitat_suitability=period_data['summary_stats']['mean_habitat_suitability'],
                    std_habitat_suitability=period_data['summary_stats']['std_habitat_suitability']
                )
            ),
            meta=result['meta']
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
