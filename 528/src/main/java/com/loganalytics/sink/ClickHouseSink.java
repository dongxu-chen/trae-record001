package com.loganalytics.sink;

import com.loganalytics.config.FlinkConfig;
import com.loganalytics.model.MetricsResult;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;

public class ClickHouseSink extends RichSinkFunction<MetricsResult> {

    private final FlinkConfig config;
    private final int batchSize;
    private final long flushIntervalMs;

    private transient Connection connection;
    private transient List<MetricsResult> batch;
    private transient ReentrantLock lock;
    private transient ScheduledExecutorService scheduler;

    public ClickHouseSink(FlinkConfig config) {
        this(config, 1000, 5000);
    }

    public ClickHouseSink(FlinkConfig config, int batchSize, long flushIntervalMs) {
        this.config = config;
        this.batchSize = batchSize;
        this.flushIntervalMs = flushIntervalMs;
    }

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);

        String url = config.getClickhouseUrl();
        String user = config.getClickhouseUser();
        String password = config.getClickhousePassword();

        connection = DriverManager.getConnection(url, user, password);
        batch = new ArrayList<>();
        lock = new ReentrantLock();

        createTableIfNotExists();

        scheduler = Executors.newSingleThreadScheduledExecutor();
        scheduler.scheduleAtFixedRate(this::flush, flushIntervalMs, flushIntervalMs, TimeUnit.MILLISECONDS);
    }

    private void createTableIfNotExists() throws Exception {
        String sql = "CREATE TABLE IF NOT EXISTS nginx_metrics (" +
                "dimension String," +
                "value String," +
                "window_start DateTime," +
                "window_end DateTime," +
                "total_requests UInt64," +
                "error_requests UInt64," +
                "error_rate Float64," +
                "qps Float64," +
                "avg_latency Float64," +
                "min_latency Float64," +
                "max_latency Float64," +
                "stddev_latency Float64," +
                "variance_latency Float64," +
                "p50_latency Float64," +
                "p95_latency Float64," +
                "p99_latency Float64," +
                "p999_latency Float64," +
                "error_rate_mean Float64," +
                "error_rate_stddev Float64," +
                "latency_mean Float64," +
                "latency_stddev Float64," +
                "qps_mean Float64," +
                "qps_stddev Float64," +
                "timestamp DateTime" +
                ") ENGINE = MergeTree() " +
                "ORDER BY (dimension, value, window_start) " +
                "PARTITION BY toDate(window_start) " +
                "TTL window_start + INTERVAL 30 DAY";

        try (PreparedStatement stmt = connection.prepareStatement(sql)) {
            stmt.execute();
        }
    }

    @Override
    public void invoke(MetricsResult metrics, Context context) throws Exception {
        lock.lock();
        try {
            batch.add(metrics);
            if (batch.size() >= batchSize) {
                flushBatch();
            }
        } finally {
            lock.unlock();
        }
    }

    private void flush() {
        lock.lock();
        try {
            if (!batch.isEmpty()) {
                flushBatch();
            }
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            lock.unlock();
        }
    }

    private void flushBatch() throws Exception {
        if (batch.isEmpty()) {
            return;
        }

        String sql = "INSERT INTO nginx_metrics (" +
                "dimension, value, window_start, window_end, total_requests, error_requests, " +
                "error_rate, qps, avg_latency, min_latency, max_latency, stddev_latency, variance_latency, " +
                "p50_latency, p95_latency, p99_latency, p999_latency, " +
                "error_rate_mean, error_rate_stddev, latency_mean, latency_stddev, qps_mean, qps_stddev, " +
                "timestamp" +
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

        try (PreparedStatement stmt = connection.prepareStatement(sql)) {
            for (MetricsResult metrics : batch) {
                int idx = 1;
                stmt.setString(idx++, metrics.getDimension());
                stmt.setString(idx++, metrics.getValue());
                stmt.setTimestamp(idx++, new Timestamp(metrics.getWindowStart()));
                stmt.setTimestamp(idx++, new Timestamp(metrics.getWindowEnd()));
                stmt.setLong(idx++, metrics.getTotalRequests());
                stmt.setLong(idx++, metrics.getErrorRequests());
                stmt.setDouble(idx++, metrics.getErrorRate());
                stmt.setDouble(idx++, metrics.getQps());
                stmt.setDouble(idx++, metrics.getAvgLatency());
                stmt.setDouble(idx++, metrics.getMinLatency());
                stmt.setDouble(idx++, metrics.getMaxLatency());
                stmt.setDouble(idx++, metrics.getStdDevLatency());
                stmt.setDouble(idx++, metrics.getVariance());
                stmt.setDouble(idx++, metrics.getP50Latency());
                stmt.setDouble(idx++, metrics.getP95Latency());
                stmt.setDouble(idx++, metrics.getP99Latency());
                stmt.setDouble(idx++, metrics.getP999Latency());
                stmt.setDouble(idx++, metrics.getErrorRateMean());
                stmt.setDouble(idx++, metrics.getErrorRateStdDev());
                stmt.setDouble(idx++, metrics.getLatencyMean());
                stmt.setDouble(idx++, metrics.getLatencyStdDev());
                stmt.setDouble(idx++, metrics.getQpsMean());
                stmt.setDouble(idx++, metrics.getQpsStdDev());
                stmt.setTimestamp(idx++, new Timestamp(metrics.getTimestamp()));
                stmt.addBatch();
            }
            stmt.executeBatch();
        }

        batch.clear();
    }

    @Override
    public void close() throws Exception {
        super.close();

        if (scheduler != null) {
            scheduler.shutdown();
            scheduler.awaitTermination(30, TimeUnit.SECONDS);
        }

        flush();

        if (connection != null && !connection.isClosed()) {
            connection.close();
        }
    }
}
