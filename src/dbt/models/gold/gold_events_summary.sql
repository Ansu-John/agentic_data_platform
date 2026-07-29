{{ config(
    materialized='table',
    table_type='iceberg',
    external_location='s3://' ~ env_var('GOLD_BUCKET_NAME') ~ '/gold_events_summary',
    format='parquet',
    write_compression='snappy'
) }}

WITH source_silver AS (
    SELECT 
        event_id,
        event_type,
        user_id,
        status,
        timestamp,
        date_parse(CAST(timestamp AS VARCHAR), '%Y-%m-%d %H:%i:%s') AS event_timestamp
    FROM {{ source('ai_catalog', 'silver_events') }}
    WHERE status IS NOT NULL
)

SELECT
    DATE_TRUNC('day', event_timestamp) AS event_date,
    event_type,
    status,
    COUNT(DISTINCT event_id) AS total_events,
    COUNT(DISTINCT user_id) AS unique_users,
    CURRENT_TIMESTAMP AS gold_processed_at
FROM source_silver
GROUP BY 1, 2, 3