import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent

# V26 is certification-native. Historical course/video archive data is not
# opened by default; the certification product owns its persistence boundary.
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

# Commercial question-bank content is deliberately outside the repository and
# outside the frontend static tree. The checked-in repository contains only the
# importer/schema/selection engine; production bank files arrive through a
# private deployment volume or secret-backed content store.
PRIVATE_QUESTION_BANK_DIR = Path(
    os.getenv(
        "PRIVATE_QUESTION_BANK_DIR",
        str(ROOT_DIR / "private_content" / "question_bank"),
    )
).expanduser()
QUESTION_BANK_AUTO_IMPORT = os.getenv("QUESTION_BANK_AUTO_IMPORT", "false").lower() in {"1", "true", "yes", "on"}

AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() in {"1", "true", "yes", "on"}
FORCE_HTTPS = os.getenv("FORCE_HTTPS", "false").lower() in {"1", "true", "yes", "on"}
SECURITY_RATE_LIMIT_ENABLED = os.getenv("SECURITY_RATE_LIMIT_ENABLED", "true").lower() in {"1", "true", "yes", "on"}

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8010").rstrip("/")

GOOGLE_AUTH_ENABLED = os.getenv("GOOGLE_AUTH_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
GOOGLE_OIDC_CLIENT_ID = os.getenv("GOOGLE_OIDC_CLIENT_ID", "").strip()
GOOGLE_OIDC_CLIENT_SECRET = os.getenv("GOOGLE_OIDC_CLIENT_SECRET", "").strip()
GOOGLE_OIDC_REDIRECT_URI = os.getenv(
    "GOOGLE_OIDC_REDIRECT_URI", f"{APP_BASE_URL}/api/auth/google/callback"
).strip()
GOOGLE_OIDC_FLOW_MINUTES = max(3, int(os.getenv("GOOGLE_OIDC_FLOW_MINUTES", "10")))

BILLING_ENABLED = os.getenv("BILLING_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_API_BASE = os.getenv("STRIPE_API_BASE", "https://api.stripe.com").rstrip("/")
STRIPE_PRICE_PREMIUM_100 = os.getenv("STRIPE_PRICE_PREMIUM_100", "").strip()
STRIPE_PRICE_PREMIUM_250 = os.getenv("STRIPE_PRICE_PREMIUM_250", "").strip()
STRIPE_PRICE_PREMIUM_500 = os.getenv("STRIPE_PRICE_PREMIUM_500", "").strip()
STRIPE_PRICE_EXAM_PACK = os.getenv("STRIPE_PRICE_EXAM_PACK", "").strip()
BILLING_PAST_DUE_GRACE_DAYS = max(0, int(os.getenv("BILLING_PAST_DUE_GRACE_DAYS", "3")))
ALLOW_MEMBERSHIP_DEV_OVERRIDE = os.getenv("ALLOW_MEMBERSHIP_DEV_OVERRIDE", "false").lower() in {"1", "true", "yes", "on"}

# No display/programmatic advertising is supported. These settings only enable
# editorial Amazon Associates links inside the authenticated Resources page.
AFFILIATE_RESOURCES_ENABLED = os.getenv("AFFILIATE_RESOURCES_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
AMAZON_ASSOCIATE_TAG = os.getenv("AMAZON_ASSOCIATE_TAG", "").strip()

EXAM_SIMULATION_CONFIG = Path(
    os.getenv(
        "EXAM_SIMULATION_CONFIG",
        str(ROOT_DIR / "config" / "exam_simulation.json"),
    )
).expanduser()
