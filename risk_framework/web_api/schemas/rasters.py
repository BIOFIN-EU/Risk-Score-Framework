from pydantic import BaseModel
from uuid import UUID
from typing import Dict, Any

class RasterData(BaseModel):
    id: str
    geo_id: UUID
    raster_bin: bytes
    raster_meta: Dict[str, Any]

    class Config:
        from_attributes = True
