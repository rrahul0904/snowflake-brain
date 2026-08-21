-- Snowflake Certification Platform public-beta feedback persistence.
-- Safe to run repeatedly. Feedback has no application TTL or automatic deletion.

CREATE TABLE IF NOT EXISTS public.beta_feedback_submissions (
  id BIGSERIAL PRIMARY KEY,
  feedback_uid UUID NOT NULL DEFAULT gen_random_uuid(),
  rating SMALLINT CHECK (rating BETWEEN 1 AND 5),
  area VARCHAR(120) NOT NULL DEFAULT 'general',
  message TEXT NOT NULL,
  email VARCHAR(320),
  context VARCHAR(220),
  route VARCHAR(180),
  theme VARCHAR(20),
  viewport VARCHAR(40),
  user_agent VARCHAR(512),
  ip_hash VARCHAR(64),
  source VARCHAR(40) NOT NULL DEFAULT 'public-beta',
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  client_created_at TIMESTAMPTZ,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT beta_feedback_uid_unique UNIQUE(feedback_uid)
);

CREATE INDEX IF NOT EXISTS idx_beta_feedback_submitted_at
  ON public.beta_feedback_submissions (submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_beta_feedback_area
  ON public.beta_feedback_submissions (area);
CREATE INDEX IF NOT EXISTS idx_beta_feedback_rating
  ON public.beta_feedback_submissions (rating);
CREATE INDEX IF NOT EXISTS idx_beta_feedback_route
  ON public.beta_feedback_submissions (route);
CREATE INDEX IF NOT EXISTS idx_beta_feedback_theme
  ON public.beta_feedback_submissions (theme);
CREATE INDEX IF NOT EXISTS idx_beta_feedback_ip_hash_submitted_at
  ON public.beta_feedback_submissions (ip_hash, submitted_at DESC)
  WHERE ip_hash IS NOT NULL;

COMMENT ON TABLE public.beta_feedback_submissions IS
  'Durable public-beta feedback. No automatic deletion; administrator deletion remains available for privacy/legal requests.';
