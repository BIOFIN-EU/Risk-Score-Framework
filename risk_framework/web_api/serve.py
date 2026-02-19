#!/usr/bin/env python
import uvicorn
from risk_framework.web_api.core import app

from risk_framework.conf import WEB_PORT, WEB_HOST

if __name__ == "__main__":
    uvicorn.run(
        "risk_framework.web_api.core:app",
        host=WEB_HOST,
        port=WEB_PORT,
        reload=True,
        log_level="debug"  # Add this instead of debug=True
    )
