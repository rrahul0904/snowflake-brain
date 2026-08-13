import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent

# V24 is certification-native. The previous course/video archive database is not
# opened by default; this gives the rebuilt product a clean schema boundary.
BRAIN_DB = Path(
    os.getenv("BRAIN_DB", str(ROOT_DIR / "data" / "snowflake_certification.sqlite"))
).expanduser()

SKILL_MAP_CONFIG = Path(
    os.getenv("SKILL_MAP_CONFIG", str(ROOT_DIR / "config" / "certification_skill_map.json"))
).expanduser()
CORE_C03_BLUEPRINT_CONFIG = Path(
    os.getenv(
        "CORE_C03_BLUEPRINT_CONFIG",
        str(ROOT_DIR / "config" / "snowpro_core_cof_c03_blueprint.json"),
    )
).expanduser()
CERTIFICATION_CATALOG_CONFIG = Path(
    os.getenv(
        "CERTIFICATION_CATALOG_CONFIG",
        str(ROOT_DIR / "config" / "certification_catalog.json"),
    )
).expanduser()
CERTIFICATION_CURRICULA_SUPPLEMENT_CONFIG = Path(
    os.getenv(
        "CERTIFICATION_CURRICULA_SUPPLEMENT_CONFIG",
        str(ROOT_DIR / "config" / "certification_curricula_supplement.json"),
    )
).expanduser()
STUDY_CONTENT_CORE_CONFIG = Path(
    os.getenv(
        "STUDY_CONTENT_CORE_CONFIG",
        str(ROOT_DIR / "config" / "study_content_core.json"),
    )
).expanduser()
SNOWFLAKE_LABS_CONFIG = Path(
    os.getenv(
        "SNOWFLAKE_LABS_CONFIG",
        str(ROOT_DIR / "config" / "snowflake_lab_challenges.json"),
    )
).expanduser()
SNOWFLAKE_LABS_MODE = os.getenv("SNOWFLAKE_LABS_MODE", "offline").lower()
