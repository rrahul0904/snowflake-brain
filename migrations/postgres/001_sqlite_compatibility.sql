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
    IF trim(modifier) <> '' THEN
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
