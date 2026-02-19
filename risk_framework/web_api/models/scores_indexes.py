from sqlalchemy import Column, String, JSON, ForeignKey, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from risk_framework.conf import DeclarativeBaseModel


class SpeciesRichnessSuitabilityIndexDB(DeclarativeBaseModel):
    __tablename__ = "species_richness_suitability_index"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    geo_id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)

    # Foreign keys to RasterData
    value_raster_id = Column(String, ForeignKey('raster_data.id'), nullable=False)
    # explainability_raster_id = Column(String, ForeignKey('raster_data.id'), nullable=False)

    # Metadata fields
    species = Column(String, nullable=False)
    country_code = Column(String, nullable=False)
    climate_scenario = Column(String, nullable=False)
    climate_model = Column(String, nullable=False)
    period = Column(String, nullable=False)
    has_humam_footprint = Column(Boolean, nullable=False)

    # Statistical fields
    mean_value = Column(Numeric, nullable=False)
    mean_std = Column(Numeric, nullable=False)
    # mean_explainability = Column(JSON, nullable=False)

    # Relationships
    value_raster = relationship("RasterData", foreign_keys=[value_raster_id])
    # explainability_raster = relationship("RasterData", foreign_keys=[explainability_raster_id])
