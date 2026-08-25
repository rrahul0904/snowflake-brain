-- Verified credential and candidate-controlled talent visibility schema.
-- Credential documents remain private storage objects; this schema stores
-- normalized issuer evidence and immutable verification events only.

CREATE TABLE IF NOT EXISTS candidate_talent_profiles (
  candidate_id BIGINT PRIMARY KEY REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  headline TEXT NOT NULL DEFAULT '',
  location TEXT NOT NULL DEFAULT '',
  availability TEXT NOT NULL DEFAULT 'not_looking'
    CHECK(availability IN ('not_looking','open_to_work','open_to_contract','available_now')),
  recruiter_discoverable INTEGER NOT NULL DEFAULT 0 CHECK(recruiter_discoverable IN (0,1)),
  public_profile INTEGER NOT NULL DEFAULT 0 CHECK(public_profile IN (0,1)),
  created_at TEXT NOT NULL DEFAULT datetime('now'),
  updated_at TEXT NOT NULL DEFAULT datetime('now')
);

CREATE TABLE IF NOT EXISTS candidate_credentials (
  credential_uid TEXT PRIMARY KEY,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  provider TEXT NOT NULL DEFAULT 'credly',
  provider_badge_id TEXT NOT NULL,
  credential_name TEXT NOT NULL DEFAULT '',
  issuer_name TEXT NOT NULL DEFAULT '',
  issued_to_name TEXT NOT NULL DEFAULT '',
  issued_at TEXT,
  expires_at TEXT,
  credential_url TEXT NOT NULL,
  verification_status TEXT NOT NULL DEFAULT 'pending'
    CHECK(verification_status IN ('pending','verified','expired','needs_review','rejected')),
  verification_method TEXT NOT NULL DEFAULT 'credly_public_url',
  verified_at TEXT,
  last_checked_at TEXT,
  verification_error TEXT NOT NULL DEFAULT '',
  evidence_hash TEXT NOT NULL DEFAULT '',
  provider_payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT datetime('now'),
  updated_at TEXT NOT NULL DEFAULT datetime('now'),
  UNIQUE(provider, provider_badge_id)
);

CREATE TABLE IF NOT EXISTS credential_verification_events (
  event_uid TEXT PRIMARY KEY,
  credential_uid TEXT NOT NULL REFERENCES candidate_credentials(credential_uid) ON DELETE CASCADE,
  candidate_id BIGINT NOT NULL REFERENCES candidate_accounts(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  from_status TEXT NOT NULL DEFAULT '',
  to_status TEXT NOT NULL,
  reason TEXT NOT NULL DEFAULT '',
  evidence_url TEXT NOT NULL DEFAULT '',
  evidence_hash TEXT NOT NULL DEFAULT '',
  checked_at TEXT NOT NULL DEFAULT datetime('now')
);

CREATE INDEX IF NOT EXISTS idx_candidate_credentials_candidate
  ON candidate_credentials(candidate_id, verification_status, updated_at);
CREATE INDEX IF NOT EXISTS idx_candidate_credentials_provider_badge
  ON candidate_credentials(provider, provider_badge_id);
CREATE INDEX IF NOT EXISTS idx_credential_verification_events_credential
  ON credential_verification_events(credential_uid, checked_at);
CREATE INDEX IF NOT EXISTS idx_candidate_talent_discoverable
  ON candidate_talent_profiles(recruiter_discoverable, public_profile, updated_at);
