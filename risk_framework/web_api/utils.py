import uuid
from typing import Optional

from risk_framework.conf import SessionLocal


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
