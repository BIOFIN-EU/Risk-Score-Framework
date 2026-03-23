from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
import uuid
from risk_framework.conf import DeclarativeBaseModel


class BaseClimateSpatialIndexScoreDB(DeclarativeBaseModel):
    __abstract__ = True

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    geo_id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    geometry = Column(String, nullable=True)  # WKT EPSG:4326
    country_code = Column(String, nullable=False)

    climate_scenario = Column(String, nullable=True)
    climate_model = Column(String, nullable=True)
    period = Column(String, nullable=True)
