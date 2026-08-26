"""Vercel Python entrypoint for the Snowflake Certification Guide.

The application itself lives in app.main so local/Docker/test and Vercel
all execute the same FastAPI instance and security/runtime boundaries.
"""

from app.main import app

__all__ = ["app"]
