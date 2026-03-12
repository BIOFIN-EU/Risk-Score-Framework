import uuid
from typing import Optional, List

from shapely.geometry import shape
import requests

from risk_framework.conf import SessionLocal, NOMINATIM_API


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_geo_uuid(species_name_list: List[str], country_code: str, wkt_polygon: Optional[str] = None) -> str:
    """
    Generate a deterministic UUID based on input parameters.
    Uses empty string for optional wkt_polygon if not provided.
    """
    # Use empty string if wkt_polygon is None
    polygon_str = wkt_polygon if wkt_polygon else ""

    species_name_list.sort()
    keys_list = species_name_list.copy()
    # Create a string combining all parameters
    keys_list.extend([country_code, polygon_str])
    input_keys_strign = '_'.join(keys_list)

    # Generate a UUID from the hash of the input string
    # UUID v5 uses a namespace and name to generate consistent UUIDs
    namespace = uuid.NAMESPACE_DNS  # You can use any fixed namespace
    cache_uuid = str(uuid.uuid5(namespace, input_keys_strign))

    return cache_uuid


def get_country_wkt(country_code):
    params = {
        'country': country_code,
        'countrycodes': country_code,
        'format': 'json',
        'polygon_geojson': 1,
        'limit': 1,
        'featuretype': 'country'
    }
    headers = {'User-Agent': 'MyApp/1.0'}

    response = requests.get(NOMINATIM_API, params=params, headers=headers)
    data = response.json()[0]
    geometry = shape(data['geojson'])
    return geometry.wkt
