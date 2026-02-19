from sqlalchemy import Column, String, JSON, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
import uuid
from risk_framework.conf import DeclarativeBaseModel

class RasterData(DeclarativeBaseModel):
    __tablename__ = "raster_data"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    geo_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    raster_bin = Column(LargeBinary, nullable=False)  # The binary raster data
    raster_meta = Column(JSON, nullable=False)  # Metadata as JSON

    def __repr__(self):
        return f"<RasterData(id={self.id}, geo_id={self.geo_id})>"
