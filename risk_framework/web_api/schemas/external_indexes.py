from pydantic import BaseModel
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field
from typing import Optional

from risk_framework.web_api.schemas.rasters import RasterDataResponse
from risk_framework.web_api.schemas.base import (
    BaseScoreIndexRequest,
    BaseRasterScoreIndexResponse,
)



class CriticalHabitatIndexRequest(BaseScoreIndexRequest):
    pass

class CriticalHabitatIndexResponse(BaseRasterScoreIndexResponse):
    class Config(BaseRasterScoreIndexResponse.Config):
        schema_extra = BaseRasterScoreIndexResponse.Config.schema_extra.copy()



class ProtectedAreaIndexRequest(BaseScoreIndexRequest):
    pass


class ProtectedAreaIndexResponse(BaseRasterScoreIndexResponse):
    class Config(BaseRasterScoreIndexResponse.Config):
        schema_extra = BaseRasterScoreIndexResponse.Config.schema_extra.copy()


