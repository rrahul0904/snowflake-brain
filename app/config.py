import os
from pathlib import Path


CONTENT_ROOT = Path(os.getenv("CONTENT_ROOT", "/content")).expanduser()
BRAIN_DB = Path(os.getenv("BRAIN_DB", "./data/snowflake_brain.sqlite")).expanduser()
AUTO_INGEST = os.getenv("AUTO_INGEST", "true").lower() == "true"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
