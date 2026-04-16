#!/bin/bash
echo $APP_PORT
gunicorn -k uvicorn.workers.UvicornWorker risk_framework.web_api.core:app --bind 0.0.0.0:$APP_PORT --workers 2 --timeout 60
