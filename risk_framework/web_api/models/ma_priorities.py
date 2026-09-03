
import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, ForeignKey, Table, JSON, Boolean
from sqlalchemy.orm import relationship


from risk_framework.conf import DeclarativeBaseModel




class PriorityManagementActionsPolygonsDB(DeclarativeBaseModel):
    __tablename__ = "priority_management_actions_polygons"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    geo_id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    geometry = Column(String, nullable=True)  # WKT EPSG:4326
    country_code = Column(String, nullable=False)
    climate_model = Column(String, nullable=True)


    risk_type  = Column(String, nullable=False)
    risk_model = Column(String, nullable=False)
    sri_species_list = Column(String, nullable=False)
    sri_correction_method = Column(String, nullable=True)
    sri_logic_type = Column(String, nullable=False)

    periods = Column(String, nullable=True)

    resilience_polygons = Column(JSON, nullable=False)
    risk_polygons = Column(JSON, nullable=False)
    recommendations_polygons = Column(JSON, nullable=False)
    recommendations_totals = Column(JSON, nullable=False)
    polygons_meta = Column(JSON, nullable=False)

