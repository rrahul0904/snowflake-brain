-- Compatibility helpers used while the application SQL surface migrates away
-- from SQLite incrementally. New migrations should use native PostgreSQL SQL.

CREATE OR REPLACE FUNCTION sqlite_datetime_impl(value text, modifiers text[])
RETURNS text
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  ts timestamptz;
  modifier text;
  normalized_modifier text;
BEGIN
  IF value IS NULL THEN
    RETURN NULL;
  END IF;

  IF lower(trim(value)) = 'now' THEN
    ts := clock_timestamp();
  ELSE
    BEGIN
      ts := value::timestamptz;
    EXCEPTION WHEN others THEN
      ts := value::timestamp AT TIME ZONE 'UTC';
    END;
  END IF;

  FOREACH modifier IN ARRAY COALESCE(modifiers, ARRAY[]::text[])
  LOOP
    normalized_modifier := lower(trim(modifier));
    IF normalized_modifier = '' THEN
      CONTINUE;
    ELSIF normalized_modifier = 'start of day' THEN
      ts := date_trunc('day', ts);
    ELSIF normalized_modifier = 'start of month' THEN
      ts := date_trunc('month', ts);
    ELSIF normalized_modifier = 'start of year' THEN
      ts := date_trunc('year', ts);
    ELSE
      ts := ts + trim(modifier)::interval;
    END IF;
  END LOOP;

  RETURN to_char(ts AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS');
END;
$$;

CREATE OR REPLACE FUNCTION datetime(value text)
RETURNS text
LANGUAGE sql
STABLE
AS $$
  SELECT sqlite_datetime_impl(value, ARRAY[]::text[])
$$;

CREATE OR REPLACE FUNCTION datetime(value text, VARIADIC modifiers text[])
RETURNS text
LANGUAGE sql
STABLE
AS $$
  SELECT sqlite_datetime_impl(value, modifiers)
$$;

-- PostgreSQL already has one-argument date casts/functions. Define the exact
-- two-argument SQLite form separately so untyped SQL literals resolve cleanly.
CREATE OR REPLACE FUNCTION date(value text, modifier text)
RETURNS text
LANGUAGE sql
STABLE
AS $$
  SELECT substring(sqlite_datetime_impl(value, ARRAY[modifier]) FROM 1 FOR 10)
$$;

-- Three-or-more SQLite date modifiers are handled by this overload.
CREATE OR REPLACE FUNCTION date(value text, first_modifier text, second_modifier text, VARIADIC modifiers text[])
RETURNS text
LANGUAGE sql
STABLE
AS $$
  SELECT substring(
    sqlite_datetime_impl(
      value,
      array_cat(ARRAY[first_modifier, second_modifier], COALESCE(modifiers, ARRAY[]::text[]))
    )
    FROM 1 FOR 10
  )
$$;
