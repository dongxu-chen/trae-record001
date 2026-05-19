const { createClient } = require('@clickhouse/client');
require('dotenv').config();

const clickhouse = createClient({
  host: `${process.env.CLICKHOUSE_HOST}:${process.env.CLICKHOUSE_PORT}`,
  database: process.env.CLICKHOUSE_DATABASE,
  username: process.env.CLICKHOUSE_USER,
  password: process.env.CLICKHOUSE_PASSWORD,
});

const initClickHouse = async () => {
  try {
    await clickhouse.exec({
      query: `CREATE DATABASE IF NOT EXISTS ${process.env.CLICKHOUSE_DATABASE}`
    });

    await clickhouse.exec({
      query: `
        CREATE TABLE IF NOT EXISTS access_logs (
          short_code String,
          long_url String,
          ip String,
          user_agent String,
          referer String,
          country String,
          region String,
          city String,
          browser String,
          os String,
          device String,
          timestamp DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (short_code, timestamp)
        TTL timestamp + INTERVAL 1 YEAR
      `
    });

    await clickhouse.exec({
      query: `
        CREATE MATERIALIZED VIEW IF NOT EXISTS stats_hourly
        ENGINE = SummingMergeTree()
        PARTITION BY toYYYYMM(hour)
        ORDER BY (short_code, hour, country, browser, os, device)
        AS SELECT
          short_code,
          toStartOfHour(timestamp) AS hour,
          country,
          browser,
          os,
          device,
          count() AS pv,
          uniq(ip) AS uv
        FROM access_logs
        GROUP BY short_code, hour, country, browser, os, device
      `
    });

    await clickhouse.exec({
      query: `
        CREATE MATERIALIZED VIEW IF NOT EXISTS stats_daily
        ENGINE = SummingMergeTree()
        PARTITION BY toYYYYMM(day)
        ORDER BY (short_code, day, country)
        AS SELECT
          short_code,
          toStartOfDay(timestamp) AS day,
          country,
          count() AS pv,
          uniq(ip) AS uv
        FROM access_logs
        GROUP BY short_code, day, country
      `
    });

    await clickhouse.exec({
      query: `
        CREATE TABLE IF NOT EXISTS heatmap_clicks (
          fingerprint String,
          session_id String,
          url String,
          path String,
          x Int32,
          y Int32,
          absolute_x Int32,
          absolute_y Int32,
          scroll_x Int32,
          scroll_y Int32,
          viewport_width Int32,
          viewport_height Int32,
          target String,
          target_id String,
          target_class String,
          timestamp DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (path, fingerprint, timestamp)
        TTL timestamp + INTERVAL 1 YEAR
      `
    });

    await clickhouse.exec({
      query: `
        CREATE TABLE IF NOT EXISTS visitor_sessions (
          fingerprint String,
          session_id String,
          ip String,
          user_agent String,
          first_seen DateTime DEFAULT now(),
          last_seen DateTime DEFAULT now(),
          visit_count Int32 DEFAULT 1,
          page_views Int32 DEFAULT 0,
          total_clicks Int32 DEFAULT 0,
          country String DEFAULT '',
          browser String DEFAULT '',
          os String DEFAULT '',
          device String DEFAULT ''
        ) ENGINE = ReplacingMergeTree(last_seen)
        PARTITION BY toYYYYMM(first_seen)
        ORDER BY (fingerprint, session_id)
        TTL first_seen + INTERVAL 1 YEAR
      `
    });

    await clickhouse.exec({
      query: `
        CREATE MATERIALIZED VIEW IF NOT EXISTS uvm_hourly
        ENGINE = SummingMergeTree()
        PARTITION BY toYYYYMM(hour)
        ORDER BY (path, hour)
        AS SELECT
          path,
          toStartOfHour(timestamp) AS hour,
          uniq(fingerprint) AS uv,
          count() AS mv,
          uniq(session_id) AS sessions
        FROM heatmap_clicks
        GROUP BY path, hour
      `
    });

    console.log('ClickHouse tables and materialized views initialized successfully');
  } catch (error) {
    console.error('ClickHouse initialization error:', error);
  }
};

module.exports = { clickhouse, initClickHouse };