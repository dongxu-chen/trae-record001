package com.loganalytics.sink;

import com.loganalytics.config.FlinkConfig;
import com.loganalytics.model.CustomMetric;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;

public class CustomMetricClickHouseSink extends RichSinkFunction<CustomMetric> {

    private static final Logger LOG = LoggerFactory.getLogger(CustomMetricClickHouseSink.class);

    private final FlinkConfig config;
    private final int batchSize;
    private final long flushIntervalMs;

    private transient Connection connection;
    private transient List<CustomMetric> batch;
    private transient ReentrantLock lock;
    private transient ScheduledExecutorService scheduler;
    private transient ObjectMapper objectMapper;

    public CustomMetricClickHouseSink(FlinkConfig config) {
        this(config, 500, 5000);
    }

    public CustomMetricClickHouseSink(FlinkConfig config, int batchSize, long flushIntervalMs) {
        this.config = config;
        this.batchSize = batchSize;
        this.flushIntervalMs = flushIntervalMs;
    }

    @Override
    public void open(Configuration parameters) throws Exception {
        super.open(parameters);
        connection = DriverManager.getConnection(config.getClickhouseUrl(), config.getClickhouseUser(), config.getClickhousePassword());
        batch = new ArrayList<>();
        lock = new ReentrantLock();
        objectMapper = new ObjectMapper();
        scheduler = Executors.newSingleThreadScheduledExecutor();
        scheduler.scheduleAtFixedRate(this::flush, flushIntervalMs, flushIntervalMs, TimeUnit.MILLISECONDS);
    }

    @Override
    public void invoke(CustomMetric metric, Context context) throws Exception {
        lock.lock();
        try {
            batch.add(metric);
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
            LOG.error("Failed to flush custom metric batch", e);
        } finally {
            lock.unlock();
        }
    }

    private void flushBatch() throws Exception {
        if (batch.isEmpty()) {
            return;
        }

        String sql = "INSERT INTO custom_metrics (" +
                "metric_name, expression, dimension, value, result, variables, timestamp" +
                ") VALUES (?, ?, ?, ?, ?, ?, ?)";

        try (PreparedStatement stmt = connection.prepareStatement(sql)) {
            for (CustomMetric m : batch) {
                int idx = 1;
                stmt.setString(idx++, m.getMetricName());
                stmt.setString(idx++, m.getExpression());
                stmt.setString(idx++, m.getDimension());
                stmt.setString(idx++, m.getValue());
                stmt.setDouble(idx++, m.getResult());
                stmt.setString(idx++, objectMapper.writeValueAsString(m.getVariables()));
                stmt.setTimestamp(idx++, new Timestamp(m.getTimestamp()));
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
