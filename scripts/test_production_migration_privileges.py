#!/usr/bin/env python3
"""Fast source-contract gate for production privilege reconciliation.

The real two-role PostgreSQL behavior is proven separately by
``test_production_role_separation_postgres.py``. This lightweight gate makes
least-privilege intent obvious and catches accidental reintroduction of broad
runtime DML/default privileges before the integration job starts.
"""

from __future__ import annotations

import io
import tokenize
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(text: str, needle: str, message: str) -> None:
    if needle not in text:
        raise AssertionError(message)


def source_without_comments(source: str) -> str:
    """Return Python source with COMMENT tokens removed but strings preserved.

    Privilege SQL is embedded in Python string literals. Searching raw source
    makes explanatory comments indistinguishable from executable SQL and caused
    a false release-gate failure. Tokenizing keeps SQL string literals intact
    while removing comments from the security assertion surface.
    """
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    return tokenize.untokenize(
        (token.type, token.string)
        for token in tokens
        if token.type != tokenize.COMMENT
    )


def main() -> None:
    migration = (ROOT / "scripts" / "migrate_production.py").read_text(encoding="utf-8")
    verifier = (ROOT / "app" / "production_schema.py").read_text(encoding="utf-8")
    executable_migration = source_without_comments(migration)

    require(migration, "RUNTIME_WRITE_TABLES", "migration job must use an explicit runtime write allowlist")
    require(migration, "REVOKE ALL PRIVILEGES ON ALL TABLES", "runtime table grants must be reset before reconciliation")
    require(migration, "GRANT SELECT ON ALL TABLES", "runtime requires read access to the migrated schema")
    require(migration, "GRANT INSERT, UPDATE, DELETE ON", "candidate/runtime state DML must be granted explicitly")
    require(migration, "REVOKE CREATE ON DATABASE", "runtime database CREATE must be revoked")
    require(migration, "REVOKE CREATE ON SCHEMA", "runtime schema CREATE must be revoked")
    require(migration, "REVOKE TRUNCATE, REFERENCES, TRIGGER", "elevated table privileges must be revoked")
    if "ALTER DEFAULT PRIVILEGES" in executable_migration:
        raise AssertionError("Runtime grants must not auto-expand through ALTER DEFAULT PRIVILEGES")

    require(verifier, '"questions",', "question table must exist in production verifier")
    require(verifier, "excessive_runtime_write", "verifier must reject writes outside the allowlist")
    require(verifier, "elevated_runtime_table_privileges", "verifier must reject TRUNCATE/REFERENCES/TRIGGER")
    require(verifier, "database_create", "verifier must reject database CREATE capability")
    require(verifier, "schema_create", "verifier must reject schema CREATE capability")

    print("Production migration privilege contract: PASS (read-all + explicit state DML; governance/DDL denied)")


if __name__ == "__main__":
    main()
