#!/usr/bin/env python3
"""Provision and rotate the least-privilege hosted PostgreSQL runtime credential.

The generated password remains in process memory only. The script reconciles
migrations/ACLs through the deployment-only database credential and upserts only
the runtime DATABASE_URL into Vercel Preview/Production as a sensitive value.
It never prints either DSN or the generated password.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import httpx
import psycopg
from psycopg import sql


RUNTIME_ROLE = os.environ.get("HOSTED_RUNTIME_ROLE", "snowflake_app_runtime").strip()
MIGRATION_URL = os.environ.get("DATABASE_MIGRATION_URL", "").strip()
VERCEL_TOKEN = os.environ.get("VERCEL_TOKEN", "").strip()
VERCEL_PROJECT_ID = os.environ.get("VERCEL_PROJECT_ID", "prj_2SLKmOpeMM8ogNkXfNYHu7IyjYab").strip()
VERCEL_TEAM_ID = os.environ.get("VERCEL_TEAM_ID", "team_zmEezpOKGZy2sH5nqTfO44LD").strip()
DATABASE_SCHEMA = os.environ.get("DATABASE_SCHEMA", "public").strip() or "public"


def require(condition: object, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def is_postgres(value: str) -> bool:
    return value.lower().startswith(("postgresql://", "postgres://"))


def runtime_dsn(admin_dsn: str, role: str, password: str) -> str:
    parsed = urlsplit(admin_dsn)
    host = parsed.hostname or ""
    require(bool(host), "Migration DSN is missing a PostgreSQL host")
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{quote(role, safe='')}:{quote(password, safe='')}@{host}{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def create_or_rotate_role(admin_dsn: str, role: str, password: str) -> None:
    parsed = urlsplit(admin_dsn)
    database_name = parsed.path.lstrip("/")
    require(bool(database_name), "Migration DSN must include a database name")
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone()
        if exists:
            conn.execute(
                sql.SQL(
                    "ALTER ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
                ).format(sql.Identifier(role), sql.Literal(password))
            )
        else:
            conn.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
                ).format(sql.Identifier(role), sql.Literal(password))
            )
        conn.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(database_name), sql.Identifier(role)
            )
        )


def upsert_vercel_runtime_dsn(value: str) -> None:
    query = urlencode({"upsert": "true", "teamId": VERCEL_TEAM_ID})
    url = f"https://api.vercel.com/v10/projects/{VERCEL_PROJECT_ID}/env?{query}"
    body = {
        "key": "DATABASE_URL",
        "value": value,
        "type": "sensitive",
        "target": ["production", "preview"],
        "comment": "Least-privilege Snowflake Certification Guide runtime PostgreSQL credential",
    }
    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            url,
            headers={"Authorization": f"Bearer {VERCEL_TOKEN}", "Content-Type": "application/json"},
            json=body,
        )
    if response.status_code not in {200, 201}:
        raise RuntimeError(f"Vercel DATABASE_URL upsert failed with HTTP {response.status_code}")
    try:
        payload = response.json()
    except Exception:
        payload = {}
    failed = payload.get("failed") if isinstance(payload, dict) else None
    if failed:
        raise RuntimeError("Vercel reported a failed DATABASE_URL upsert")


def main() -> None:
    require(is_postgres(MIGRATION_URL), "DATABASE_MIGRATION_URL must be the deployment-only PostgreSQL credential")
    require(bool(VERCEL_TOKEN), "VERCEL_TOKEN is required to rotate the hosted runtime credential")
    require(bool(RUNTIME_ROLE), "HOSTED_RUNTIME_ROLE must not be empty")

    password = secrets.token_urlsafe(36)
    generated_runtime_dsn = runtime_dsn(MIGRATION_URL, RUNTIME_ROLE, password)
    create_or_rotate_role(MIGRATION_URL, RUNTIME_ROLE, password)

    # Import application modules only after the in-memory runtime DSN is set so
    # app.config sees the new credential and the verifier tests the exact role
    # that will be installed in Vercel.
    os.environ["DATABASE_URL"] = generated_runtime_dsn
    os.environ["DATABASE_MIGRATION_URL"] = MIGRATION_URL
    os.environ["DATABASE_SCHEMA"] = DATABASE_SCHEMA
    os.environ["POSTGRES_TEST_ISOLATION"] = "false"
    os.environ.pop("VERCEL", None)
    os.environ.pop("VERCEL_ENV", None)

    from app.postgres_backend import close_pool, run_postgres_migrations
    from app.production_schema import assert_production_schema_ready
    from scripts.migrate_production import grant_runtime_privileges

    try:
        run_postgres_migrations(migration_url=MIGRATION_URL)
        grant_runtime_privileges()
        status = assert_production_schema_ready()
        require(status.get("status") == "ok", "Least-privilege runtime verification failed after ACL reconciliation")
        require(status.get("runtime_role") == RUNTIME_ROLE, "Runtime verifier authenticated as an unexpected PostgreSQL role")
        upsert_vercel_runtime_dsn(generated_runtime_dsn)
    finally:
        close_pool()

    # Never include the password or DSNs in output/artifacts.
    print(
        json.dumps(
            {
                "status": "ok",
                "runtime_role": RUNTIME_ROLE,
                "database_schema": DATABASE_SCHEMA,
                "vercel_project_id": VERCEL_PROJECT_ID,
                "vercel_targets": ["production", "preview"],
                "runtime_dsn_rotated": True,
                "redeploy_required": True,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Hosted runtime provisioning failed: {type(exc).__name__}", file=sys.stderr)
        raise
