from sqlalchemy import Column, String, ForeignKey, Table, JSON, Boolean
from sqlalchemy.orm import relationship

from risk_framework.web_api.models.base import BaseClimateSpatialIndexScoreDB

from risk_framework.conf import DeclarativeBaseModel


risk_chi_link = Table(
    "risk_chi_link",
    DeclarativeBaseModel.metadata,
    Column("biodiversity_risk_index", String, ForeignKey("biodiversity_risk_index.id")),
    Column("chi_id", String, ForeignKey("critical_habitat_index.id"))
)

risk_pai_link = Table(
    "risk_pai_link",
    DeclarativeBaseModel.metadata,
    Column("biodiversity_risk_index", String, ForeignKey("biodiversity_risk_index.id")),
    Column("pai_id", String, ForeignKey("protected_area_index.id"))
)

risk_sri_link = Table(
    "risk_sri_link",
    DeclarativeBaseModel.metadata,
    Column("biodiversity_risk_index", String, ForeignKey("biodiversity_risk_index.id")),
    Column("sri_id", String, ForeignKey("species_richness_index.id"))
)




class BiodiversityRiskIndexDB(BaseClimateSpatialIndexScoreDB):
    __tablename__ = "biodiversity_risk_index"

    risk_type  = Column(String, nullable=False)

    # Foreign keys to RasterData
    green_value_raster_id = Column(String, ForeignKey('raster_data.id'), nullable=False)
    green_value_raster = relationship("RasterDataDB", foreign_keys=[green_value_raster_id])

    urban_value_raster_id = Column(String, ForeignKey('raster_data.id'), nullable=False)
    urban_value_raster = relationship("RasterDataDB", foreign_keys=[urban_value_raster_id])

    xai_raster_id = Column(String, ForeignKey('raster_data.id'), nullable=False)
    xai_raster = relationship("RasterDataDB", foreign_keys=[xai_raster_id])
    xai_summary_json = Column(JSON, nullable=False)  # General Explainability data as JSON

    risk_model = Column(String, nullable=False) #(YangEtAl2021/SihamEtAl2026/PontesEtAl2026)?
    risk_ling_thresholds_json = Column(JSON, nullable=False)
    crop_to_polygon = Column(Boolean, nullable=False)


    sri_species_list = Column(String, nullable=False)
    sri_correction_method = Column(String, nullable=True)
    sri_logic_type = Column(String, nullable=False)

    # Foreign keys for one-to-one relationships
    chi_related_id = Column(String, ForeignKey('critical_habitat_index.id'), nullable=False)
    pai_related_id = Column(String, ForeignKey('protected_area_index.id'),  nullable=False)
    sri_related_id = Column(String, ForeignKey('species_richness_index.id'), nullable=False)

    # One-to-one relationships
    chi_related = relationship("CriticalHabitatIndexDB", foreign_keys=[chi_related_id])
    pai_related = relationship("ProtectedAreaIndexDB", foreign_keys=[pai_related_id])
    sri_related = relationship("SpeciesRichnessIndexDB", foreign_keys=[sri_related_id])
