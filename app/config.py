import os
from pathlib import Path


CONTENT_ROOT = Path(os.getenv("CONTENT_ROOT", "/content")).expanduser()
BRAIN_DB = Path(os.getenv("BRAIN_DB", "./data/snowflake_brain.sqlite")).expanduser()
AUTO_INGEST = os.getenv("AUTO_INGEST", "true").lower() == "true"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

ROOT_DIR = Path(__file__).resolve().parent.parent
SKILL_MAP_CONFIG = Path(os.getenv("SKILL_MAP_CONFIG", str(ROOT_DIR / "config" / "certification_skill_map.json"))).expanduser()
SNOWFLAKE_LABS_CONFIG = Path(os.getenv("SNOWFLAKE_LABS_CONFIG", str(ROOT_DIR / "config" / "snowflake_lab_challenges.json"))).expanduser()
SNOWFLAKE_LABS_MODE = os.getenv("SNOWFLAKE_LABS_MODE", "offline").lower()
