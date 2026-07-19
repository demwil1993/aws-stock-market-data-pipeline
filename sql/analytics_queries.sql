-- =============================================================================
-- Athena Analytics Queries
-- =============================================================================
-- Project: AWS Stock Market Data Pipeline
--
-- Purpose:
--     This script contains analytical queries for the curated stock quote layer.
--     The curated layer is stored in Amazon S3 as partitioned Parquet files and
--     registered in the AWS Glue Data Catalog.
--
-- Source table:
--     curated_quotes
--
-- Notes:
--     - Run these queries using the project Athena workgroup.
--     - market_timestamp and ingestion_timestamp are TIMESTAMP columns.
--     - year, month, and day are partition columns stored as strings.
-- =============================================================================


-- =============================================================================
-- 1. Preview curated stock quote data
-- =============================================================================

SELECT
    symbol,
    company_name,
    exchange,
    currency,
    price,
    open_price,
    high_price,
    low_price,
    previous_close,
    change,
    change_percent,
    volume,
    market_timestamp,
    ingestion_timestamp,
    source,
    year,
    month,
    day
FROM curated_quotes
ORDER BY market_timestamp DESC, symbol
LIMIT 50;


-- =============================================================================
-- 2. Latest available quote for each stock symbol
-- =============================================================================
-- Returns the most recently available record for every symbol.

WITH ranked_quotes AS (
    SELECT
        symbol,
        company_name,
        exchange,
        currency,
        price,
        open_price,
        high_price,
        low_price,
        previous_close,
        change,
        change_percent,
        volume,
        market_timestamp,
        ingestion_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY symbol
            ORDER BY market_timestamp DESC, ingestion_timestamp DESC
        ) AS row_num
    FROM curated_quotes
)

SELECT
    symbol,
    company_name,
    exchange,
    currency,
    price,
    open_price,
    high_price,
    low_price,
    previous_close,
    change,
    change_percent,
    volume,
    market_timestamp,
    ingestion_timestamp
FROM ranked_quotes
WHERE row_num = 1
ORDER BY symbol;


-- =============================================================================
-- 3. Latest market gainers
-- =============================================================================
-- Ranks the latest quote for each symbol by percentage gain.

WITH latest_quotes AS (
    SELECT
        symbol,
        company_name,
        exchange,
        price,
        change,
        change_percent,
        volume,
        market_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY symbol
            ORDER BY market_timestamp DESC, ingestion_timestamp DESC
        ) AS row_num
    FROM curated_quotes
)

SELECT
    symbol,
    company_name,
    exchange,
    price,
    change,
    change_percent,
    volume,
    market_timestamp
FROM latest_quotes
WHERE row_num = 1
  AND change_percent > 0
ORDER BY change_percent DESC
LIMIT 10;


-- =============================================================================
-- 4. Latest market losers
-- =============================================================================
-- Ranks the latest quote for each symbol by percentage loss.

WITH latest_quotes AS (
    SELECT
        symbol,
        company_name,
        exchange,
        price,
        change,
        change_percent,
        volume,
        market_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY symbol
            ORDER BY market_timestamp DESC, ingestion_timestamp DESC
        ) AS row_num
    FROM curated_quotes
)

SELECT
    symbol,
    company_name,
    exchange,
    price,
    change,
    change_percent,
    volume,
    market_timestamp
FROM latest_quotes
WHERE row_num = 1
  AND change_percent < 0
ORDER BY change_percent
LIMIT 10;


-- =============================================================================
-- 5. Highest-volume stocks from the latest quote
-- =============================================================================

WITH latest_quotes AS (
    SELECT
        symbol,
        company_name,
        exchange,
        price,
        change_percent,
        volume,
        market_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY symbol
            ORDER BY market_timestamp DESC, ingestion_timestamp DESC
        ) AS row_num
    FROM curated_quotes
)

SELECT
    symbol,
    company_name,
    exchange,
    price,
    change_percent,
    volume,
    market_timestamp
FROM latest_quotes
WHERE row_num = 1
ORDER BY volume DESC
LIMIT 10;


-- =============================================================================
-- 6. Price range analysis
-- =============================================================================
-- Calculates the dollar and percentage range between the daily high and low.

SELECT
    symbol,
    company_name,
    price,
    high_price,
    low_price,
    high_price - low_price AS price_range,
    ROUND(
        ((high_price - low_price) / NULLIF(low_price, 0)) * 100,
        2
    ) AS price_range_percent,
    market_timestamp
FROM curated_quotes
WHERE high_price IS NOT NULL
  AND low_price IS NOT NULL
ORDER BY price_range_percent DESC, market_timestamp DESC;


-- =============================================================================
-- 7. Daily stock summary
-- =============================================================================
-- Aggregates all records for each stock and market date.

SELECT
    symbol,
    CAST(market_timestamp AS DATE) AS market_date,
    MIN(low_price) AS daily_low,
    MAX(high_price) AS daily_high,
    AVG(price) AS average_observed_price,
    MAX(volume) AS reported_volume,
    COUNT(*) AS quote_count
FROM curated_quotes
GROUP BY
    symbol,
    CAST(market_timestamp AS DATE)
ORDER BY market_date DESC, symbol;


-- =============================================================================
-- 8. Exchange-level market summary
-- =============================================================================

SELECT
    exchange,
    COUNT(DISTINCT symbol) AS symbol_count,
    COUNT(*) AS quote_count,
    ROUND(AVG(price), 2) AS average_stock_price,
    ROUND(AVG(change_percent), 2) AS average_change_percent,
    SUM(volume) AS total_reported_volume
FROM curated_quotes
GROUP BY exchange
ORDER BY total_reported_volume DESC;


-- =============================================================================
-- 9. Daily market performance summary
-- =============================================================================
-- Shows the number of gaining, losing, and unchanged stocks by market date.

WITH daily_latest_quotes AS (
    SELECT
        symbol,
        CAST(market_timestamp AS DATE) AS market_date,
        change_percent,
        ROW_NUMBER() OVER (
            PARTITION BY
                symbol,
                CAST(market_timestamp AS DATE)
            ORDER BY market_timestamp DESC, ingestion_timestamp DESC
        ) AS row_num
    FROM curated_quotes
)

SELECT
    market_date,
    COUNT(*) AS symbol_count,
    SUM(CASE WHEN change_percent > 0 THEN 1 ELSE 0 END) AS gaining_symbols,
    SUM(CASE WHEN change_percent < 0 THEN 1 ELSE 0 END) AS losing_symbols,
    SUM(CASE WHEN change_percent = 0 THEN 1 ELSE 0 END) AS unchanged_symbols,
    ROUND(AVG(change_percent), 2) AS average_change_percent
FROM daily_latest_quotes
WHERE row_num = 1
GROUP BY market_date
ORDER BY market_date DESC;


-- =============================================================================
-- 10. Seven-observation moving average
-- =============================================================================
-- Calculates a rolling average using the current quote and six prior quotes.
-- This is observation-based rather than calendar-day-based.

SELECT
    symbol,
    market_timestamp,
    price,
    ROUND(
        AVG(price) OVER (
            PARTITION BY symbol
            ORDER BY market_timestamp
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS seven_observation_moving_average
FROM curated_quotes
ORDER BY symbol, market_timestamp;


-- =============================================================================
-- 11. Day-over-day closing price movement
-- =============================================================================
-- Uses the latest quote for each symbol and market date before applying LAG.

WITH daily_latest_quotes AS (
    SELECT
        symbol,
        CAST(market_timestamp AS DATE) AS market_date,
        price,
        market_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY
                symbol,
                CAST(market_timestamp AS DATE)
            ORDER BY market_timestamp DESC, ingestion_timestamp DESC
        ) AS row_num
    FROM curated_quotes
),

daily_prices AS (
    SELECT
        symbol,
        market_date,
        price
    FROM daily_latest_quotes
    WHERE row_num = 1
),

price_history AS (
    SELECT
        symbol,
        market_date,
        price,
        LAG(price) OVER (
            PARTITION BY symbol
            ORDER BY market_date
        ) AS previous_day_price
    FROM daily_prices
)

SELECT
    symbol,
    market_date,
    price,
    previous_day_price,
    price - previous_day_price AS day_over_day_change,
    ROUND(
        (
            (price - previous_day_price)
            / NULLIF(previous_day_price, 0)
        ) * 100,
        2
    ) AS day_over_day_change_percent
FROM price_history
WHERE previous_day_price IS NOT NULL
ORDER BY market_date DESC, symbol;


-- =============================================================================
-- 12. Historical price volatility by symbol
-- =============================================================================
-- Uses standard deviation of price and percentage change as volatility measures.

SELECT
    symbol,
    company_name,
    COUNT(*) AS observation_count,
    ROUND(AVG(price), 2) AS average_price,
    ROUND(MIN(price), 2) AS minimum_price,
    ROUND(MAX(price), 2) AS maximum_price,
    ROUND(STDDEV_SAMP(price), 2) AS price_standard_deviation,
    ROUND(STDDEV_SAMP(change_percent), 2) AS change_percent_standard_deviation
FROM curated_quotes
GROUP BY
    symbol,
    company_name
HAVING COUNT(*) > 1
ORDER BY change_percent_standard_deviation DESC;


-- =============================================================================
-- 13. Data freshness report
-- =============================================================================
-- Compares the latest market timestamp and ingestion timestamp for each symbol.

SELECT
    symbol,
    MAX(market_timestamp) AS latest_market_timestamp,
    MAX(ingestion_timestamp) AS latest_ingestion_timestamp,
    DATE_DIFF(
        'minute',
        MAX(market_timestamp),
        MAX(ingestion_timestamp)
    ) AS market_to_ingestion_delay_minutes
FROM curated_quotes
GROUP BY symbol
ORDER BY latest_market_timestamp DESC, symbol;


-- =============================================================================
-- 14. Curated partition summary
-- =============================================================================
-- Shows the number of rows and symbols stored in each S3 partition.

SELECT
    year,
    month,
    day,
    COUNT(*) AS row_count,
    COUNT(DISTINCT symbol) AS symbol_count,
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