from sqlalchemy import Column, String, ForeignKey, Table
from sqlalchemy.orm import relationship

from risk_framework.web_api.models.base import BaseClimateSpatialIndexScoreDB

from risk_framework.conf import DeclarativeBaseModel


hsi_sri_link = Table(
    "hsi_sri_link",
    DeclarativeBaseModel.metadata,
    Column("hsi_id", String, ForeignKey("species_habitat_suitability_index.id")),
    Column("sri_id", String, ForeignKey("species_richness_index.id"))
)

class SpeciesHabitatSuitabilityIndexDB(BaseClimateSpatialIndexScoreDB):
    __tablename__ = "species_habitat_suitability_index"

    # Foreign keys to RasterData
    value_raster_id = Column(String, ForeignKey('raster_data.id'), nullable=False)
    value_raster = relationship("RasterDataDB", foreign_keys=[value_raster_id])
    # explainability_raster_id = Column(String, ForeignKey('raster_data.id'), nullable=False)

    # Metadata fields
    species = Column(String, nullable=False)
    # mean_explainability = Column(JSON, nullable=False)

    # Relationships
    # explainability_raster = relationship("RasterData", foreign_keys=[explainability_raster_id])
    sri_related = relationship(
        "SpeciesRichnessIndexDB",
        secondary=hsi_sri_link,
        back_populates="hsi_related"
    )


class SpeciesRichnessIndexDB(BaseClimateSpatialIndexScoreDB):
    __tablename__ = "species_richness_index"

    # Foreign keys to RasterData
    value_raster_id = Column(String, ForeignKey('raster_data.id'), nullable=False)
    value_raster = relationship("RasterDataDB", foreign_keys=[value_raster_id])
    # Metadata fields
    species_list = Column(String, nullable=False)
    correction_method = Column(String, nullable=True)
    logic_type = Column(String, nullable=False) #fuzzy/crisp

    hsi_related = relationship(
        "SpeciesHabitatSuitabilityIndexDB",
        secondary=hsi_sri_link,
        back_populates="sri_related"
    )
