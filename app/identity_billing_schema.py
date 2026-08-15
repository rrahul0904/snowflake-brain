from __future__ import annotations

import sqlite3
import threading

from .database import connect


SCHEMA_VERSION = "20260814_009_google_identity_billing_authority_v26"
_SCHEMA_LOCK = threading.RLock()
_READY_DATABASES: set[str] = set()


def _database_key(conn: sqlite3.Connection) -> str:
    row = conn.execute("PRAGMA database_list").fetchone()
    if not row:
        return "unknown"
    try:
        return str(row["file"] or row[2] or "memory")
    except (KeyError, TypeError, IndexError):
        return str(row[2] or "memory")


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, declaration: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")


def ensure_identity_billing_schema() -> None:
    """Additive V26 migration for external identities and trusted billing state.

    This helper is called from authentication dependencies as a defensive
    compatibility boundary as well as from application startup. Keep it safe
    under concurrent requests: after a database has been migrated successfully
    in this process, later calls are no-ops instead of repeatedly dropping and
    recreating schema objects.
    """
    with _SCHEMA_LOCK:
        with connect() as conn:
            database_key = _database_key(conn)
            if database_key in _READY_DATABASES:
                return

            _ensure_column(conn, "candidate_accounts", "password_login_enabled", "INTEGER NOT NULL DEFAULT 1")
            _ensure_column(conn, "candidate_memberships", "entitlement_version", "INTEGER NOT NULL DEFAULT 1")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS candidate_identities (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
                  provider TEXT NOT NULL,
                  provider_subject TEXT NOT NULL,
                  provider_email TEXT DEFAULT '',
                  provider_email_verified INTEGER NOT NULL DEFAULT 0,
                  created_at TEXT DEFAULT (datetime('now')),
                  last_login_at TEXT DEFAULT (datetime('now')),
                  UNIQUE(provider, provider_subject)
                );

                CREATE TABLE IF NOT EXISTS oauth_login_flows (
                  state_hash TEXT PRIMARY KEY,
                  provider TEXT NOT NULL,
                  nonce TEXT NOT NULL,
                  code_verifier TEXT NOT NULL,
                  created_at TEXT DEFAULT (datetime('now')),
                  expires_at TEXT NOT NULL,
                  consumed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS pending_identity_links (
                  token_hash TEXT PRIMARY KEY,
                  candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
                  provider TEXT NOT NULL,
                  provider_subject TEXT NOT NULL,
                  provider_email TEXT NOT NULL,
                  provider_email_verified INTEGER NOT NULL DEFAULT 0,
                  created_at TEXT DEFAULT (datetime('now')),
                  expires_at TEXT NOT NULL,
                  consumed_at TEXT,
                  UNIQUE(provider, provider_subject)
                );

                CREATE TABLE IF NOT EXISTS billing_customers (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
                  provider TEXT NOT NULL,
                  provider_customer_id TEXT NOT NULL,
                  created_at TEXT DEFAULT (datetime('now')),
                  updated_at TEXT DEFAULT (datetime('now')),
                  UNIQUE(provider, candidate_id),
                  UNIQUE(provider, provider_customer_id)
                );

                CREATE TABLE IF NOT EXISTS billing_checkout_sessions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
                  provider TEXT NOT NULL,
                  provider_checkout_session_id TEXT NOT NULL,
                  provider_customer_id TEXT NOT NULL,
                  provider_price_id TEXT NOT NULL,
                  internal_plan TEXT NOT NULL,
                  checkout_mode TEXT NOT NULL,
                  status TEXT NOT NULL DEFAULT 'pending',
                  created_at TEXT DEFAULT (datetime('now')),
                  completed_at TEXT,
                  UNIQUE(provider, provider_checkout_session_id)
                );

                CREATE TABLE IF NOT EXISTS billing_subscriptions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
                  provider TEXT NOT NULL,
                  provider_customer_id TEXT NOT NULL,
                  provider_subscription_id TEXT NOT NULL,
                  provider_price_id TEXT NOT NULL,
                  internal_plan TEXT NOT NULL,
                  status TEXT NOT NULL,
                  current_period_start TEXT,
                  current_period_end TEXT,
                  cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
                  last_provider_event_created INTEGER NOT NULL DEFAULT 0,
                  created_at TEXT DEFAULT (datetime('now')),
                  updated_at TEXT DEFAULT (datetime('now')),
                  UNIQUE(provider, provider_subscription_id)
                );

                CREATE TABLE IF NOT EXISTS billing_purchases (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
                  provider TEXT NOT NULL,
                  provider_payment_id TEXT NOT NULL,
                  product_type TEXT NOT NULL,
                  status TEXT NOT NULL,
                  purchased_at TEXT DEFAULT (datetime('now')),
                  expires_at TEXT,
                  metadata_json TEXT NOT NULL DEFAULT '{}',
                  UNIQUE(provider, provider_payment_id)
                );

                CREATE TABLE IF NOT EXISTS billing_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  provider TEXT NOT NULL,
                  provider_event_id TEXT NOT NULL,
                  event_type TEXT NOT NULL,
                  received_at TEXT DEFAULT (datetime('now')),
                  processed_at TEXT,
                  processing_status TEXT NOT NULL DEFAULT 'received',
                  payload_hash TEXT NOT NULL,
                  error_message TEXT DEFAULT '',
                  UNIQUE(provider, provider_event_id)
                );

                CREATE TABLE IF NOT EXISTS membership_audit_log (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  candidate_id INTEGER NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
                  old_plan TEXT NOT NULL,
                  new_plan TEXT NOT NULL,
                  reason TEXT NOT NULL,
                  source TEXT NOT NULL,
                  provider_event_id TEXT,
                  entitlement_version INTEGER NOT NULL,
                  created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_candidate_identities_candidate
                  ON candidate_identities(candidate_id, provider);
                CREATE INDEX IF NOT EXISTS idx_pending_identity_links_candidate
                  ON pending_identity_links(candidate_id, expires_at);
                CREATE INDEX IF NOT EXISTS idx_billing_customers_candidate
                  ON billing_customers(candidate_id, provider);
                CREATE INDEX IF NOT EXISTS idx_billing_checkout_candidate
                  ON billing_checkout_sessions(candidate_id, status, created_at);
                CREATE INDEX IF NOT EXISTS idx_billing_subscriptions_candidate
                  ON billing_subscriptions(candidate_id, status, updated_at);
                CREATE INDEX IF NOT EXISTS idx_billing_purchases_candidate
                  ON billing_purchases(candidate_id, product_type, status);
                CREATE INDEX IF NOT EXISTS idx_membership_audit_candidate
                  ON membership_audit_log(candidate_id, created_at);
                """
            )
            # Upgrade databases created by earlier V26 feature revisions too.
            _ensure_column(conn, "billing_subscriptions", "last_provider_event_created", "INTEGER NOT NULL DEFAULT 0")

            migrated = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE version=? LIMIT 1",
                (SCHEMA_VERSION,),
            ).fetchone()
            if not migrated:
                conn.executescript(
                    """
                    DROP TRIGGER IF EXISTS trg_restore_exam_pack_after_membership_expiry;
                    CREATE TRIGGER IF NOT EXISTS trg_restore_exam_pack_after_membership_expiry
                    AFTER UPDATE OF status ON candidate_memberships
                    WHEN OLD.status = 'active'
                     AND NEW.status = 'expired'
                     AND EXISTS (
                       SELECT 1 FROM billing_purchases p
                       WHERE p.candidate_id = NEW.candidate_id
                         AND p.product_type = 'exam_pack_35'
                         AND p.status = 'paid'
                     )
                     AND NOT EXISTS (
                       SELECT 1 FROM candidate_memberships m
                       WHERE m.candidate_id = NEW.candidate_id
                         AND m.status = 'active'
                         AND datetime(m.starts_at) <= datetime('now')
                         AND (m.expires_at IS NULL OR datetime(m.expires_at) > datetime('now'))
                     )
                    BEGIN
                      INSERT INTO candidate_memberships(
                        candidate_id,tier,plan_code,status,starts_at,expires_at,source,entitlement_version
                      )
                      VALUES (
                        NEW.candidate_id,'premium','exam_pack_35','active',datetime('now'),NULL,
                        'entitlement_reconciliation',
                        COALESCE((SELECT MAX(entitlement_version) FROM candidate_memberships WHERE candidate_id=NEW.candidate_id),0)+1
                      );
                      UPDATE candidate_accounts
                         SET plan='premium',updated_at=datetime('now')
                       WHERE id=NEW.candidate_id;
                      INSERT INTO membership_audit_log(
                        candidate_id,old_plan,new_plan,reason,source,provider_event_id,entitlement_version
                      )
                      SELECT NEW.candidate_id,NEW.plan_code,'exam_pack_35',
                             'expired_subscription_exam_pack_fallback','entitlement_reconciliation',NULL,
                             MAX(entitlement_version)
                        FROM candidate_memberships
                       WHERE candidate_id=NEW.candidate_id;
                    END;
                    """
                )
                conn.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, name) VALUES (?, ?)",
                    (SCHEMA_VERSION, "Google OIDC identities, ordered billing authority, entitlement versioning, and Exam Pack expiry reconciliation"),
                )

            _READY_DATABASES.add(database_key)
