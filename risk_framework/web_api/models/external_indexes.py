from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship

from risk_framework.web_api.models.base import BaseClimateSpatialIndexScoreDB




class CriticalHabitatIndexDB(BaseClimateSpatialIndexScoreDB):
    __tablename__ = "critical_habitat_index"

    # Foreign keys to RasterData
    value_raster_id = Column(String, ForeignKey('raster_data.id'), nullable=False)
    value_raster = relationship("RasterDataDB", foreign_keys=[value_raster_id])



class ProtectedAreaIndexDB(BaseClimateSpatialIndexScoreDB):
    __tablename__ = "protected_area_index"

    # Foreign keys to RasterData
    value_raster_id = Column(String, ForeignKey('raster_data.id'), nullable=False)
    value_raster = relationship("RasterDataDB", foreign_keys=[value_raster_id])
