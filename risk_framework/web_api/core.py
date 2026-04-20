from functools import partial
import logging
import uuid
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.routing import APIRoute
from sqlalchemy import text
from sqlalchemy.orm import Session
from risk_framework.conf import engine, SessionLocal, DeclarativeBaseModel
from risk_framework.web_api.routes import hsi_router, sri_router, others_router, risk_router

logger = logging.getLogger(__name__)

class Application(FastAPI):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_session = SessionLocal
        self.setup_database()
        self.api_version = 'v1'
        self.api_versioned_root_path = f'/api/{self.api_version}'
        self.include_router(hsi_router, prefix=f"{self.api_versioned_root_path}/hsi")
        self.include_router(sri_router, prefix=f"{self.api_versioned_root_path}/sri")
        self.include_router(others_router, prefix=f"{self.api_versioned_root_path}/others")
        self.include_router(risk_router, prefix=f"{self.api_versioned_root_path}/risk")

    def setup_database(self):
        """Setup database lifecycle handlers"""

        async def db_startup(app: Application):
            """Create tables on startup if they don't exist"""
            logger.info("Creating database tables if they don't exist...")

            # Import models so they are registered with DeclarativeBaseModel
            from risk_framework.web_api.models import scores_indexes, rasters, external_indexes

            # Create all tables
            DeclarativeBaseModel.metadata.create_all(bind=engine)
            logger.info("Database tables ready!")

            # Test database connection
            try:
                with app.db_session() as db:
                    db.execute(text("SELECT 1"))
                    logger.info("Database connection successful!")
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                raise

        async def db_shutdown(app: Application):
            """Cleanup on shutdown"""
            logger.info("Shutting down database connections...")
            # Dispose the engine connection pool
            engine.dispose()
            logger.info("Database connections closed!")

        self.add_event_handler("startup", partial(db_startup, app=self))
        self.add_event_handler("shutdown", partial(db_shutdown, app=self))

    def get_db(self):
        """Dependency to get database session"""
        db = self.db_session()
        try:
            yield db
        finally:
            db.close()

# Create the application instance
app = Application(
    title="Risk Framework API",
    description="API for biodiversity risk assessment",
    version="0.1.0",
    default_response_class=ORJSONResponse
)
