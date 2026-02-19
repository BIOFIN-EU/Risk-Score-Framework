#!/usr/bin/env python
import uvicorn
from risk_framework.web_api.api import app

from risk_framework.conf import WEB_PORT, WEB_HOST

if __name__ == "__main__":
    uvicorn.run(
        "risk_framework.web_api.api:app",
        host=WEB_HOST,
        port=WEB_PORT,
        reload=True,
    )
