-- =============================================================================
-- Athena Curated-Layer Validation Queries
-- =============================================================================
-- Project: AWS Stock Market Data Pipeline
--
-- Purpose:
--     Validate the quality, integrity, completeness, and partitioning of the
--     curated stock quote table.
--
-- Expected results:
--     Queries labeled "Expectation: No rows" should return zero records.
--     Summary queries should be reviewed for reasonable values.
--
-- Source table:
--     curated_quotes
-- =============================================================================


-- =============================================================================
-- 1. Required-column null or blank checks
-- =============================================================================
-- Expectation: No rows

SELECT
    symbol,
    price,
    market_timestamp,
    ingestion_timestamp
FROM curated_quotes
WHERE symbol IS NULL
   OR TRIM(symbol) = ''
   OR price IS NULL
   OR market_timestamp IS NULL
   OR ingestion_timestamp IS NULL;


-- =============================================================================
-- 2. Invalid price values
-- =============================================================================
-- Expectation: No rows

SELECT
    symbol,
    price,
    market_timestamp
FROM curated_quotes
WHERE price <= 0;


-- =============================================================================
-- 3. Negative volume
-- =============================================================================
-- Expectation: No rows
-- NULL volume is allowed because some API responses may not provide volume.

SELECT
    symbol,
    volume,
    market_timestamp
FROM curated_quotes
WHERE volume < 0;


-- =============================================================================
-- 4. High price below low price
-- =============================================================================
-- Expectation: No rows

SELECT
    symbol,
    high_price,
    low_price,
    market_timestamp
FROM curated_quotes
WHERE high_price IS NOT NULL
  AND low_price IS NOT NULL
  AND high_price < low_price;


-- =============================================================================
-- 5. Price outside the reported daily range
-- =============================================================================
-- Expectation: No rows when high_price and low_price are populated

SELECT
    symbol,
    price,
    high_price,
    low_price,
    market_timestamp
FROM curated_quotes
WHERE high_price IS NOT NULL
  AND low_price IS NOT NULL
  AND (
        price > high_price
        OR price < low_price
      );


-- =============================================================================
-- 6. Duplicate business keys
-- =============================================================================
-- The curated ETL job deduplicates on symbol and market_timestamp.
-- Expectation: No rows

SELECT
    symbol,
    market_timestamp,
    COUNT(*) AS duplicate_count
FROM curated_quotes
GROUP BY
    symbol,
    market_timestamp
HAVING COUNT(*) > 1;


-- =============================================================================
-- 7. Duplicate business keys with record details
-- =============================================================================
-- Use this query for investigation only if Query 6 finds duplicates.
-- Expectation: No rows

WITH duplicate_keys AS (
    SELECT
        symbol,
        market_timestamp
    FROM curated_quotes
    GROUP BY
        symbol,
        market_timestamp
    HAVING COUNT(*) > 1
)

SELECT
    q.*
FROM curated_quotes AS q
INNER JOIN duplicate_keys AS d
    ON q.symbol = d.symbol
   AND q.market_timestamp = d.market_timestamp
ORDER BY
    q.symbol,
    q.market_timestamp,
    q.ingestion_timestamp;


-- =============================================================================
-- 8. Symbol normalization
-- =============================================================================
-- Symbols should be trimmed and uppercase.
-- Expectation: No rows

SELECT
    symbol,
    market_timestamp
FROM curated_quotes
WHERE symbol <> UPPER(TRIM(symbol));


-- =============================================================================
-- 9. Exchange normalization
-- =============================================================================
-- Exchange values should be trimmed and uppercase when populated.
-- Expectation: No rows

SELECT
    symbol,
    exchange,
    market_timestamp
FROM curated_quotes
WHERE exchange IS NOT NULL
  AND exchange <> UPPER(TRIM(exchange));


-- =============================================================================
-- 10. Currency normalization
-- =============================================================================
-- Currency values should be trimmed and uppercase when populated.
-- Expectation: No rows

SELECT
    symbol,
    currency,
    market_timestamp
FROM curated_quotes
WHERE currency IS NOT NULL
  AND currency <> UPPER(TRIM(currency));


-- =============================================================================
-- 11. Source normalization
-- =============================================================================
-- The ETL job standardizes source values to lowercase.
-- Expectation: No rows

SELECT
    symbol,
    source,
    market_timestamp
FROM curated_quotes
WHERE source IS NOT NULL
  AND source <> LOWER(TRIM(source));


-- =============================================================================
-- 12. Market timestamp after ingestion timestamp
-- =============================================================================
-- A market observation should not normally occur after it was ingested.
-- Expectation: No rows

SELECT
    symbol,
    market_timestamp,
    ingestion_timestamp,
    DATE_DIFF(
        'minute',
        ingestion_timestamp,
        market_timestamp
    ) AS market_ahead_minutes
FROM curated_quotes
WHERE market_timestamp > ingestion_timestamp;


-- =============================================================================
-- 13. Excessive ingestion delay
-- =============================================================================
-- Flags records ingested more than 24 hours after their market timestamp.
-- Review any results; historical backfills may legitimately exceed this limit.

SELECT
    symbol,
    market_timestamp,
    ingestion_timestamp,
    DATE_DIFF(
        'hour',
        market_timestamp,
        ingestion_timestamp
    ) AS ingestion_delay_hours
FROM curated_quotes
WHERE DATE_DIFF(
        'hour',
        market_timestamp,
        ingestion_timestamp
      ) > 24
ORDER BY ingestion_delay_hours DESC;


-- =============================================================================
-- 14. Partition values compared with market timestamp
-- =============================================================================
-- Partition fields should match the date in market_timestamp.
-- Expectation: No rows

SELECT
    symbol,
    market_timestamp,
    year,
    month,
    day
FROM curated_quotes
WHERE year <> DATE_FORMAT(market_timestamp, '%Y')
   OR month <> DATE_FORMAT(market_timestamp, '%m')
   OR day <> DATE_FORMAT(market_timestamp, '%d');


-- =============================================================================
-- 15. Invalid partition formats
-- =============================================================================
-- Expectation: No rows

SELECT
    symbol,
    year,
    month,
    day,
    market_timestamp
FROM curated_quotes
WHERE year IS NULL
   OR month IS NULL
   OR day IS NULL
   OR NOT REGEXP_LIKE(year, '^[0-9]{4}$')
   OR NOT REGEXP_LIKE(month, '^(0[1-9]|1[0-2])$')
   OR NOT REGEXP_LIKE(day, '^(0[1-9]|[12][0-9]|3[01])$');


-- =============================================================================
-- 16. Change calculation consistency
-- =============================================================================
-- change should approximately equal price minus previous_close.
-- A tolerance is used to account for decimal precision and source rounding.
-- Expectation: No rows, except possible source-specific rounding differences.

SELECT
    symbol,
    price,
    previous_close,
    change,
    price - previous_close AS calculated_change,
    ABS(change - (price - previous_close)) AS difference,
    market_timestamp
FROM curated_quotes
WHERE price IS NOT NULL
  AND previous_close IS NOT NULL
  AND change IS NOT NULL
  AND ABS(change - (price - previous_close)) > 0.02;


-- =============================================================================
-- 17. Percentage-change calculation consistency
-- =============================================================================
-- change_percent should approximately equal change / previous_close * 100.
-- A tolerance is used for source rounding.
-- Expectation: No rows, except possible source-specific rounding differences.

SELECT
    symbol,
    previous_close,
    change,
    change_percent,
    ROUND(
        (change / NULLIF(previous_close, 0)) * 100,
        4
    ) AS calculated_change_percent,
    ABS(
        change_percent
        - ((change / NULLIF(previous_close, 0)) * 100)
    ) AS difference,
    market_timestamp
FROM curated_quotes
WHERE previous_close IS NOT NULL
  AND previous_close <> 0
  AND change IS NOT NULL
  AND change_percent IS NOT NULL
  AND ABS(
        change_percent
        - ((change / previous_close) * 100)
      ) > 0.05;


-- =============================================================================
-- 18. OHLC consistency
-- =============================================================================
-- The daily high should not be below open, price, or previous close.
-- The daily low should not be above open or price.
-- Previous close may be outside today's range, so it is not checked against
-- today's high and low.
-- Expectation: No rows

SELECT
    symbol,
    open_price,
    high_price,
    low_price,
    price,
    market_timestamp
FROM curated_quotes
WHERE (
        high_price IS NOT NULL
        AND open_price IS NOT NULL
        AND high_price < open_price
      )
   OR (
        high_price IS NOT NULL
        AND price IS NOT NULL
        AND high_price < price
      )
   OR (
        low_price IS NOT NULL
        AND open_price IS NOT NULL
        AND low_price > open_price
      )
   OR (
        low_price IS NOT NULL
        AND price IS NOT NULL
        AND low_price > price
      );


-- =============================================================================
-- 19. Row count by partition
-- =============================================================================
-- Review for missing or unexpectedly small partitions.

SELECT
    year,
    month,
    day,
    COUNT(*) AS row_count,
    COUNT(DISTINCT symbol) AS distinct_symbol_count,
    MIN(market_timestamp) AS earliest_market_timestamp,
    MAX(market_timestamp) AS latest_market_timestamp
FROM curated_quotes
GROUP BY
    year,
    month,
    day
ORDER BY
    year DESC,
    month DESC,
    day DESC;


-- =============================================================================
-- 20. Record count by symbol
-- =============================================================================
-- Review for symbols with unexpectedly missing history.

SELECT
    symbol,
    company_name,
    COUNT(*) AS record_count,
    MIN(market_timestamp) AS earliest_market_timestamp,
    MAX(market_timestamp) AS latest_market_timestamp
FROM curated_quotes
GROUP BY
    symbol,
    company_name
ORDER BY
    record_count DESC,
    symbol;


-- =============================================================================
-- 21. Null-profile summary
-- =============================================================================
-- Provides column-level null counts across the curated table.

SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN symbol IS NULL THEN 1 ELSE 0 END) AS symbol_nulls,
    SUM(CASE WHEN company_name IS NULL THEN 1 ELSE 0 END) AS company_name_nulls,
    SUM(CASE WHEN exchange IS NULL THEN 1 ELSE 0 END) AS exchange_nulls,
    SUM(CASE WHEN currency IS NULL THEN 1 ELSE 0 END) AS currency_nulls,
    SUM(CASE WHEN price IS NULL THEN 1 ELSE 0 END) AS price_nulls,
    SUM(CASE WHEN open_price IS NULL THEN 1 ELSE 0 END) AS open_price_nulls,
    SUM(CASE WHEN high_price IS NULL THEN 1 ELSE 0 END) AS high_price_nulls,
    SUM(CASE WHEN low_price IS NULL THEN 1 ELSE 0 END) AS low_price_nulls,
    SUM(CASE WHEN previous_close IS NULL THEN 1 ELSE 0 END)
        AS previous_close_nulls,
    SUM(CASE WHEN change IS NULL THEN 1 ELSE 0 END) AS change_nulls,
    SUM(CASE WHEN change_percent IS NULL THEN 1 ELSE 0 END)
        AS change_percent_nulls,
    SUM(CASE WHEN volume IS NULL THEN 1 ELSE 0 END) AS volume_nulls,
    SUM(CASE WHEN market_timestamp IS NULL THEN 1 ELSE 0 END)
        AS market_timestamp_nulls,
    SUM(CASE WHEN ingestion_timestamp IS NULL THEN 1 ELSE 0 END)
        AS ingestion_timestamp_nulls,
    SUM(CASE WHEN source IS NULL THEN 1 ELSE 0 END) AS source_nulls
FROM curated_quotes;


-- =============================================================================
-- 22. Overall curated-layer validation summary
-- =============================================================================
-- Produces one row with the major data-quality failure counts.
-- All failure counts should ideally equal zero.

SELECT
    COUNT(*) AS total_rows,

    SUM(
        CASE
            WHEN symbol IS NULL OR TRIM(symbol) = ''
            THEN 1 ELSE 0
        END
    ) AS invalid_symbol_rows,

    SUM(
        CASE
            WHEN price IS NULL OR price <= 0
            THEN 1 ELSE 0
        END
    ) AS invalid_price_rows,

    SUM(
        CASE
            WHEN market_timestamp IS NULL
            THEN 1 ELSE 0
        END
    ) AS invalid_market_timestamp_rows,

    SUM(
        CASE
            WHEN ingestion_timestamp IS NULL
            THEN 1 ELSE 0
        END
    ) AS invalid_ingestion_timestamp_rows,

    SUM(
        CASE
            WHEN volume < 0
            THEN 1 ELSE 0
        END
    ) AS negative_volume_rows,

    SUM(
        CASE
            WHEN high_price IS NOT NULL
             AND low_price IS NOT NULL
             AND high_price < low_price
            THEN 1 ELSE 0
        END
    ) AS invalid_high_low_rows,

    SUM(
        CASE
            WHEN market_timestamp > ingestion_timestamp
            THEN 1 ELSE 0
        END
    ) AS future_market_timestamp_rows,

    SUM(
        CASE
            WHEN year <> DATE_FORMAT(market_timestamp, '%Y')
              OR month <> DATE_FORMAT(market_timestamp, '%m')
              OR day <> DATE_FORMAT(market_timestamp, '%d')
            THEN 1 ELSE 0
        END
    ) AS partition_mismatch_rows
FROM curated_quotes;