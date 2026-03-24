import uuid
import pickle

from sqlalchemy.orm import joinedload

from risk_framework.web_api.models import (
    CriticalHabitatIndexDB,
    RasterDataDB,
)
from risk_framework.web_api.schemas import (
    CriticalHabitatIndexResponse,
    RasterDataResponse,
    RasterSummaryStats,
)
from risk_framework.web_api.utils import (
    get_country_wkt
)
from risk_framework.species_models.ch_model import (
    CHModel
)



def retrieve_or_calculate_ch(country_code, wkt_polygon, geo_id, db):
    country_code = country_code.upper()

    query = db.query(CriticalHabitatIndexDB).options(
        joinedload(CriticalHabitatIndexDB.value_raster)
    )

    query = query.filter(
        CriticalHabitatIndexDB.geo_id == geo_id,
    )

    # existing_record = query.first()
    existing_record = None
    # If record exists, retrieve it and return cached result
    if not existing_record:
        existing_record = run_and_create_new_ch_record(
            geo_id,
            country_code.upper(),
            wkt_polygon,
            db
        )

    existing_raster_value = pickle.loads(existing_record.value_raster.raster_bin)

    return CriticalHabitatIndexResponse(
        id=existing_record.id,
        country_code=existing_record.country_code,
        geometry=existing_record.geometry,
        raster_data=RasterDataResponse(
            raster=existing_raster_value,
            summary_stats=RasterSummaryStats(
                mean_raster_value=float(existing_record.value_raster.mean_value),
                std_raster_value=float(existing_record.value_raster.mean_std)
            ),
            meta=existing_record.value_raster.raster_meta
        )
    )

def run_and_create_new_ch_record(geo_id, country_code, wkt_polygon, db):
    if wkt_polygon == "" or wkt_polygon is None:
        wkt_polygon = get_country_wkt(country_code)

    model = CHModel(country_code, wkt_polygon=wkt_polygon, db=db)

    result = model.run()

    scenario_record = create_ch_and_raster_records(
        geo_id, result, db)

    return scenario_record

def create_ch_and_raster_records(geo_id, result, db):
    country_code = result['country_code']
    wkt_polygon = result['wkt_polygon']

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

    # db.add(new_raster_data)
    # db.flush()

    new_record = CriticalHabitatIndexDB(
        id=str(uuid.uuid4()),
        geo_id=geo_id,
        value_raster_id=new_raster_data.id,
        geometry=wkt_polygon,
        country_code=country_code,
    )

    # db.add(new_record)
    # db.commit()
    new_record.value_raster = new_raster_data
    return new_record

