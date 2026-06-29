LABS = [
    {
        "id": "warehouse-foundations",
        "title": "Warehouse Foundations",
        "level": "Core",
        "minutes": 35,
        "domain": "Architecture",
        "objectives": [
            "Create a database, schema, warehouse, table, and file format.",
            "Load starter data with COPY INTO.",
            "Validate load history and warehouse behavior.",
        ],
        "setup": "Use a Snowflake trial account or a sandbox role with CREATE DATABASE and CREATE WAREHOUSE privileges.",
        "steps": [
            "Create a dedicated warehouse for lab work.",
            "Create a lab database and schema.",
            "Create a CSV file format and stage.",
            "Load a small dataset into a table.",
            "Inspect query history and load history.",
        ],
        "validation": [
            "The WAREHOUSE exists and can be suspended/resumed.",
            "The ORDERS table returns rows.",
            "COPY_HISTORY shows a successful load.",
        ],
        "sql": """CREATE OR REPLACE WAREHOUSE LAB_WH
  WAREHOUSE_SIZE = XSMALL
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;

CREATE OR REPLACE DATABASE SNOWPRO_LAB;
CREATE OR REPLACE SCHEMA SNOWPRO_LAB.CORE;

CREATE OR REPLACE FILE FORMAT SNOWPRO_LAB.CORE.CSV_FF
  TYPE = CSV
  SKIP_HEADER = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"';

CREATE OR REPLACE TABLE SNOWPRO_LAB.CORE.ORDERS (
  ORDER_ID NUMBER,
  CUSTOMER_ID NUMBER,
  ORDER_TS TIMESTAMP_NTZ,
  AMOUNT NUMBER(10,2)
);

-- Upload a CSV into this stage from Snowsight, then run COPY INTO.
CREATE OR REPLACE STAGE SNOWPRO_LAB.CORE.ORDERS_STAGE
  FILE_FORMAT = SNOWPRO_LAB.CORE.CSV_FF;

COPY INTO SNOWPRO_LAB.CORE.ORDERS
FROM @SNOWPRO_LAB.CORE.ORDERS_STAGE;

SELECT COUNT(*) AS ROWS_LOADED FROM SNOWPRO_LAB.CORE.ORDERS;""",
    },
    {
        "id": "time-travel-clone",
        "title": "Time Travel and Zero-Copy Clone",
        "level": "Core",
        "minutes": 30,
        "domain": "Continuity",
        "objectives": [
            "Recover data with Time Travel.",
            "Create a zero-copy clone for safe testing.",
            "Compare clone behavior against source tables.",
        ],
        "setup": "Run after the Warehouse Foundations lab or point the table names at an existing sandbox table.",
        "steps": [
            "Clone the lab database.",
            "Update rows in the clone.",
            "Query historical source data.",
            "Restore a dropped table from Time Travel.",
        ],
        "validation": [
            "The clone is queryable without copying table storage up front.",
            "Historical queries return the pre-change version.",
            "UNDROP restores a dropped table inside the retention period.",
        ],
        "sql": """CREATE OR REPLACE DATABASE SNOWPRO_LAB_DEV
  CLONE SNOWPRO_LAB;

UPDATE SNOWPRO_LAB_DEV.CORE.ORDERS
SET AMOUNT = AMOUNT * 1.10
WHERE AMOUNT IS NOT NULL;

SELECT COUNT(*) FROM SNOWPRO_LAB.CORE.ORDERS
AT (OFFSET => -60 * 5);

DROP TABLE SNOWPRO_LAB_DEV.CORE.ORDERS;
UNDROP TABLE SNOWPRO_LAB_DEV.CORE.ORDERS;

SELECT DATABASE_NAME, RETENTION_TIME
FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASES
WHERE DATABASE_NAME IN ('SNOWPRO_LAB', 'SNOWPRO_LAB_DEV');""",
    },
    {
        "id": "variant-flatten",
        "title": "Semi-Structured Data with VARIANT",
        "level": "Core",
        "minutes": 40,
        "domain": "Data Loading",
        "objectives": [
            "Store JSON data in a VARIANT column.",
            "Use dot notation and FLATTEN.",
            "Create typed relational projections from nested data.",
        ],
        "setup": "Requires a role that can create objects in the lab database.",
        "steps": [
            "Create a raw events table.",
            "Insert JSON payloads with PARSE_JSON.",
            "Extract scalar values with path notation.",
            "Flatten nested arrays into rows.",
        ],
        "validation": [
            "Nested attributes can be queried without predefining the whole schema.",
            "FLATTEN returns one row per array element.",
            "The typed projection filters correctly by event type.",
        ],
        "sql": """CREATE OR REPLACE TABLE SNOWPRO_LAB.CORE.EVENTS_RAW (
  EVENT_ID NUMBER,
  PAYLOAD VARIANT
);

INSERT INTO SNOWPRO_LAB.CORE.EVENTS_RAW
SELECT 1, PARSE_JSON('{"type":"purchase","customer":{"id":42},"items":[{"sku":"A1","qty":2},{"sku":"B2","qty":1}]}')
UNION ALL
SELECT 2, PARSE_JSON('{"type":"refund","customer":{"id":42},"items":[{"sku":"A1","qty":1}]}');

SELECT
  EVENT_ID,
  PAYLOAD:type::STRING AS EVENT_TYPE,
  PAYLOAD:customer.id::NUMBER AS CUSTOMER_ID
FROM SNOWPRO_LAB.CORE.EVENTS_RAW;

SELECT
  E.EVENT_ID,
  I.VALUE:sku::STRING AS SKU,
  I.VALUE:qty::NUMBER AS QTY
FROM SNOWPRO_LAB.CORE.EVENTS_RAW E,
LATERAL FLATTEN(INPUT => E.PAYLOAD:items) I;""",
    },
    {
        "id": "streams-tasks",
        "title": "Streams and Tasks Pipeline",
        "level": "Advanced",
        "minutes": 45,
        "domain": "Pipelines",
        "objectives": [
            "Track table changes with a stream.",
            "Process changes with a scheduled task.",
            "Understand task warehouse and scheduling choices.",
        ],
        "setup": "Use a sandbox warehouse. Keep tasks suspended until you are ready to test.",
        "steps": [
            "Create a source table and target table.",
            "Create a stream on the source table.",
            "Create a task that consumes stream changes.",
            "Insert data and manually execute the task.",
        ],
        "validation": [
            "The stream shows pending rows after inserts.",
            "The task moves rows into the target table.",
            "The stream offset advances after successful consumption.",
        ],
        "sql": """CREATE OR REPLACE TABLE SNOWPRO_LAB.CORE.RAW_ORDERS (
  ORDER_ID NUMBER,
  AMOUNT NUMBER(10,2),
  INGESTED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR REPLACE TABLE SNOWPRO_LAB.CORE.ORDER_FACTS (
  ORDER_ID NUMBER,
  AMOUNT NUMBER(10,2),
  PROCESSED_AT TIMESTAMP_NTZ
);

CREATE OR REPLACE STREAM SNOWPRO_LAB.CORE.RAW_ORDERS_STREAM
  ON TABLE SNOWPRO_LAB.CORE.RAW_ORDERS;

CREATE OR REPLACE TASK SNOWPRO_LAB.CORE.LOAD_ORDER_FACTS
  WAREHOUSE = LAB_WH
  SCHEDULE = '5 MINUTE'
  WHEN SYSTEM$STREAM_HAS_DATA('SNOWPRO_LAB.CORE.RAW_ORDERS_STREAM')
AS
INSERT INTO SNOWPRO_LAB.CORE.ORDER_FACTS
SELECT ORDER_ID, AMOUNT, CURRENT_TIMESTAMP()
FROM SNOWPRO_LAB.CORE.RAW_ORDERS_STREAM
WHERE METADATA$ACTION = 'INSERT';

INSERT INTO SNOWPRO_LAB.CORE.RAW_ORDERS (ORDER_ID, AMOUNT)
VALUES (1001, 19.99), (1002, 41.50);

EXECUTE TASK SNOWPRO_LAB.CORE.LOAD_ORDER_FACTS;
SELECT * FROM SNOWPRO_LAB.CORE.ORDER_FACTS;""",
    },
    {
        "id": "rbac-least-privilege",
        "title": "RBAC Least Privilege",
        "level": "Core",
        "minutes": 35,
        "domain": "Security",
        "objectives": [
            "Model functional roles and access roles.",
            "Grant warehouse and schema privileges cleanly.",
            "Verify permissions with SHOW GRANTS.",
        ],
        "setup": "Requires SECURITYADMIN or a delegated security role in a non-production account.",
        "steps": [
            "Create access and functional roles.",
            "Grant warehouse usage and schema/table privileges.",
            "Assign access roles to functional roles.",
            "Review inherited grants.",
        ],
        "validation": [
            "The analyst role can query selected tables.",
            "The role cannot modify data unless explicitly granted.",
            "SHOW GRANTS confirms the role hierarchy.",
        ],
        "sql": """USE ROLE SECURITYADMIN;

CREATE ROLE IF NOT EXISTS AR_SNOWPRO_CORE_READ;
CREATE ROLE IF NOT EXISTS FR_SNOWPRO_ANALYST;

GRANT USAGE ON WAREHOUSE LAB_WH TO ROLE AR_SNOWPRO_CORE_READ;
GRANT USAGE ON DATABASE SNOWPRO_LAB TO ROLE AR_SNOWPRO_CORE_READ;
GRANT USAGE ON SCHEMA SNOWPRO_LAB.CORE TO ROLE AR_SNOWPRO_CORE_READ;
GRANT SELECT ON ALL TABLES IN SCHEMA SNOWPRO_LAB.CORE TO ROLE AR_SNOWPRO_CORE_READ;
GRANT SELECT ON FUTURE TABLES IN SCHEMA SNOWPRO_LAB.CORE TO ROLE AR_SNOWPRO_CORE_READ;

GRANT ROLE AR_SNOWPRO_CORE_READ TO ROLE FR_SNOWPRO_ANALYST;

SHOW GRANTS TO ROLE AR_SNOWPRO_CORE_READ;
SHOW GRANTS TO ROLE FR_SNOWPRO_ANALYST;""",
    },
    {
        "id": "cost-performance",
        "title": "Cost and Performance Drill",
        "level": "Advanced",
        "minutes": 50,
        "domain": "Performance",
        "objectives": [
            "Compare warehouse sizing and auto-suspend settings.",
            "Inspect query history and bytes scanned.",
            "Create guardrails with a resource monitor.",
        ],
        "setup": "Use a sandbox account. Resource monitor creation may require ACCOUNTADMIN.",
        "steps": [
            "Run the same query with different warehouse sizes.",
            "Review QUERY_HISTORY for execution metrics.",
            "Set an auto-suspend policy.",
            "Create a small resource monitor for lab warehouses.",
        ],
        "validation": [
            "Warehouse settings reflect intended suspend/resume behavior.",
            "Query history shows elapsed time and bytes scanned.",
            "The resource monitor is attached to the lab warehouse.",
        ],
        "sql": """ALTER WAREHOUSE LAB_WH SET
  WAREHOUSE_SIZE = XSMALL
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;

SELECT *
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_WAREHOUSE(
  WAREHOUSE_NAME => 'LAB_WH',
  RESULT_LIMIT => 20
))
ORDER BY START_TIME DESC;

USE ROLE ACCOUNTADMIN;

CREATE OR REPLACE RESOURCE MONITOR LAB_MONITOR
  WITH CREDIT_QUOTA = 5
  FREQUENCY = MONTHLY
  TRIGGERS
    ON 75 PERCENT DO NOTIFY
    ON 100 PERCENT DO SUSPEND;

ALTER WAREHOUSE LAB_WH SET RESOURCE_MONITOR = LAB_MONITOR;""",
    },
]
