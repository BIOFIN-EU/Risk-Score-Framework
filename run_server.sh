#!/bin/bash
echo $WEB_PORT
gunicorn -k uvicorn.workers.UvicornWorker risk_framework.web_api.core:app --bind 0.0.0.0:$WEB_PORT --workers 2 --timeout 0
