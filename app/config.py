import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent

# V26 is certification-native. Historical course/video archive data is not
# opened by default; the certification product owns its persistence boundary.
BRAIN_DB = Path(
    os.getenv("BRAIN_DB", str(ROOT_DIR / "data" / "snowflake_certification.sqlite"))
).expanduser()

# Production persistence. Local development and tests remain SQLite by default;
# setting DATABASE_URL to PostgreSQL switches the shared database API to the
# pooled PostgreSQL adapter. POSTGRES_TEST_ISOLATION is CI-only and gives each
# test process a private schema while exercising the same PostgreSQL server.
#
# Every hosted Vercel function (Preview and Production) must remain cloud-only
# and verification-only. A preview can otherwise mutate the same managed
# database accidentally, which is just as dangerous as a production function
# performing DDL itself.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
# This credential is deliberately separate from the runtime pool. It is used
# only by the controlled migration job and must never be configured on a Vercel
# runtime deployment. Keeping the two credentials distinct lets the runtime
# role remain DML-only.
DATABASE_MIGRATION_URL = os.getenv("DATABASE_MIGRATION_URL", "").strip()
VERCEL_ENV = os.getenv("VERCEL_ENV", "").strip().lower()
IS_VERCEL_PRODUCTION = VERCEL_ENV == "production"
IS_VERCEL_RUNTIME = (
    os.getenv("VERCEL", "").strip() == "1"
    or VERCEL_ENV in {"preview", "production"}
)
IS_POSTGRES_URL = DATABASE_URL.lower().startswith(("postgresql://", "postgres://"))

if IS_VERCEL_RUNTIME and not DATABASE_URL:
    raise RuntimeError(
        "Vercel database configuration error: DATABASE_URL is required for every "
        "Preview/Production runtime; SQLite fallback is disabled."
    )
if IS_VERCEL_RUNTIME and not IS_POSTGRES_URL:
    raise RuntimeError(
        "Vercel database configuration error: DATABASE_URL must be a PostgreSQL "
        "connection URL for every Preview/Production runtime; SQLite fallback is disabled."
    )
if IS_VERCEL_RUNTIME and DATABASE_MIGRATION_URL:
    raise RuntimeError(
        "Vercel database configuration error: DATABASE_MIGRATION_URL must not be "
        "available to a request-serving runtime. Run migrations from an approved deployment job."
    )
DATABASE_BACKEND = "postgresql" if IS_POSTGRES_URL else "sqlite"
DATABASE_SCHEMA = os.getenv("DATABASE_SCHEMA", "public").strip() or "public"
DB_POOL_MIN_SIZE = max(1, int(os.getenv("DB_POOL_MIN_SIZE", "2")))
DB_POOL_MAX_SIZE = max(DB_POOL_MIN_SIZE, int(os.getenv("DB_POOL_MAX_SIZE", "12")))
DB_POOL_TIMEOUT_SECONDS = max(1, int(os.getenv("DB_POOL_TIMEOUT_SECONDS", "10")))
# Serverless functions can be frozen long enough for the database or a network
# proxy to close an otherwise idle socket. Keep pooled connections short-lived
# and validate every checkout so a thawed function reconnects before serving.
DB_POOL_MAX_IDLE_SECONDS = max(1, int(os.getenv("DB_POOL_MAX_IDLE_SECONDS", "60")))
DB_POOL_MAX_LIFETIME_SECONDS = max(1, int(os.getenv("DB_POOL_MAX_LIFETIME_SECONDS", "300")))
DB_POOL_RECONNECT_TIMEOUT_SECONDS = max(1, int(os.getenv("DB_POOL_RECONNECT_TIMEOUT_SECONDS", "10")))
POSTGRES_TEST_ISOLATION = os.getenv("POSTGRES_TEST_ISOLATION", "false").lower() in {"1", "true", "yes", "on"}
POSTGRES_TEST_SCHEMA_PREFIX = os.getenv("POSTGRES_TEST_SCHEMA_PREFIX", "snowflake_ci").strip() or "snowflake_ci"

# Vendor-neutral production observability. JSON stdout remains the default
# centralized-log integration surface; optional error/alert webhooks can forward
# sanitized operational events to Sentry-style gateways, incident systems, or a
# deployment-owned telemetry collector without introducing provider lock-in.
OBSERVABILITY_ENABLED = os.getenv("OBSERVABILITY_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
OBSERVABILITY_LOG_LEVEL = os.getenv("OBSERVABILITY_LOG_LEVEL", "INFO").strip().upper() or "INFO"
OBSERVABILITY_METRICS_TOKEN = os.getenv("OBSERVABILITY_METRICS_TOKEN", "").strip()
OBSERVABILITY_ERROR_WEBHOOK_URL = os.getenv("OBSERVABILITY_ERROR_WEBHOOK_URL", "").strip()
OBSERVABILITY_ALERT_WEBHOOK_URL = os.getenv("OBSERVABILITY_ALERT_WEBHOOK_URL", "").strip()
OBSERVABILITY_WINDOW_SECONDS = max(60, int(os.getenv("OBSERVABILITY_WINDOW_SECONDS", "300")))
OBSERVABILITY_5XX_ALERT_THRESHOLD = max(1, int(os.getenv("OBSERVABILITY_5XX_ALERT_THRESHOLD", "5")))
OBSERVABILITY_AUTH_FAILURE_ALERT_THRESHOLD = max(1, int(os.getenv("OBSERVABILITY_AUTH_FAILURE_ALERT_THRESHOLD", "10")))
OBSERVABILITY_ALERT_COOLDOWN_SECONDS = max(30, int(os.getenv("OBSERVABILITY_ALERT_COOLDOWN_SECONDS", "300")))
OBSERVABILITY_MAX_LATENCY_SAMPLES = max(100, int(os.getenv("OBSERVABILITY_MAX_LATENCY_SAMPLES", "2000")))

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
# controlled administrative import job, never a request-serving Vercel function.
PRIVATE_QUESTION_BANK_DIR = Path(
    os.getenv(
        "PRIVATE_QUESTION_BANK_DIR",
        str(ROOT_DIR / "private_content" / "question_bank"),
    )
).expanduser()
QUESTION_BANK_AUTO_IMPORT = os.getenv("QUESTION_BANK_AUTO_IMPORT", "false").lower() in {"1", "true", "yes", "on"}

if IS_VERCEL_RUNTIME and QUESTION_BANK_AUTO_IMPORT:
    raise RuntimeError(
        "Vercel question-bank configuration error: QUESTION_BANK_AUTO_IMPORT "
        "must be false. Import releases through the controlled administrative job."
    )

AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() in {"1", "true", "yes", "on"}
FORCE_HTTPS = os.getenv("FORCE_HTTPS", "false").lower() in {"1", "true", "yes", "on"}
SECURITY_RATE_LIMIT_ENABLED = os.getenv("SECURITY_RATE_LIMIT_ENABLED", "true").lower() in {"1", "true", "yes", "on"}

# Hosted request-serving runtimes must fail closed if deployment settings drift
# to an insecure state. Local/test environments remain configurable so the same
# application can be exercised over HTTP in isolated CI.
if IS_VERCEL_RUNTIME and not AUTH_COOKIE_SECURE:
    raise RuntimeError("Vercel security configuration error: AUTH_COOKIE_SECURE must be true")
if IS_VERCEL_RUNTIME and not FORCE_HTTPS:
    raise RuntimeError("Vercel security configuration error: FORCE_HTTPS must be true")
if IS_VERCEL_RUNTIME and not SECURITY_RATE_LIMIT_ENABLED:
    raise RuntimeError("Vercel security configuration error: SECURITY_RATE_LIMIT_ENABLED must be true")

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8010").rstrip("/")
if IS_VERCEL_RUNTIME and not APP_BASE_URL.lower().startswith("https://"):
    raise RuntimeError("Vercel security configuration error: APP_BASE_URL must use HTTPS")

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
STRIPE_PORTAL_CONFIGURATION_ID = os.getenv("STRIPE_PORTAL_CONFIGURATION_ID", "").strip()
STRIPE_API_BASE = os.getenv("STRIPE_API_BASE", "https://api.stripe.com").rstrip("/")
STRIPE_PRICE_PREMIUM_100 = os.getenv("STRIPE_PRICE_PREMIUM_100", "").strip()
STRIPE_PRICE_PREMIUM_250 = os.getenv("STRIPE_PRICE_PREMIUM_250", "").strip()
STRIPE_PRICE_PREMIUM_500 = os.getenv("STRIPE_PRICE_PREMIUM_500", "").strip()
STRIPE_PRICE_EXAM_PACK = os.getenv("STRIPE_PRICE_EXAM_PACK", "").strip()
BILLING_PAST_DUE_GRACE_DAYS = max(0, int(os.getenv("BILLING_PAST_DUE_GRACE_DAYS", "3")))
ALLOW_MEMBERSHIP_DEV_OVERRIDE = os.getenv("ALLOW_MEMBERSHIP_DEV_OVERRIDE", "false").lower() in {"1", "true", "yes", "on"}
if IS_VERCEL_RUNTIME and ALLOW_MEMBERSHIP_DEV_OVERRIDE:
    raise RuntimeError("Vercel security configuration error: ALLOW_MEMBERSHIP_DEV_OVERRIDE must be false")

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
