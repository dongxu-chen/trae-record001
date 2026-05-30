package com.loganalytics.sink;

import com.loganalytics.config.FlinkConfig;
import com.loganalytics.model.TrafficForecast;
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
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;

public class ForecastClickHouseSink extends RichSinkFunction<TrafficForecast> {

    private static final Logger LOG = LoggerFactory.getLogger(ForecastClickHouseSink.class);

    private final FlinkConfig config;
    private final int batchSize;
    private final long flushIntervalMs;

    private transient Connection connection;
    private transient List<TrafficForecast> batch;
    private transient ReentrantLock lock;
    private transient ScheduledExecutorService scheduler;

    public ForecastClickHouseSink(FlinkConfig config) {
        this(config, 500, 5000);
    }

    public ForecastClickHouseSink(FlinkConfig config, int batchSize, long flushIntervalMs) {
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
        scheduler = Executors.newSingleThreadScheduledExecutor();
        scheduler.scheduleAtFixedRate(this::flush, flushIntervalMs, flushIntervalMs, TimeUnit.MILLISECONDS);
    }

    @Override
    public void invoke(TrafficForecast forecast, Context context) throws Exception {
        lock.lock();
        try {
            batch.add(forecast);
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
            LOG.error("Failed to flush forecast batch", e);
        } finally {
            lock.unlock();
        }
    }

    private void flushBatch() throws Exception {
        if (batch.isEmpty()) {
            return;
        }

        String sql = "INSERT INTO traffic_forecasts (" +
                "dimension, value, current_qps, predicted_qps, predicted_qps_next, predicted_qps_next2, " +
                "confidence, trend_slope, trend_intercept, trend_direction, " +
                "moving_avg5, moving_avg10, deviation_from_predicted, " +
                "window_start, window_end, timestamp" +
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

        try (PreparedStatement stmt = connection.prepareStatement(sql)) {
            for (TrafficForecast f : batch) {
                int idx = 1;
                stmt.setString(idx++, f.getDimension());
                stmt.setString(idx++, f.getValue());
                stmt.setDouble(idx++, f.getCurrentQps());
                stmt.setDouble(idx++, f.getPredictedQps());
                stmt.setDouble(idx++, f.getPredictedQpsNext());
                stmt.setDouble(idx++, f.getPredictedQpsNext2());
                stmt.setDouble(idx++, f.getConfidence());
                stmt.setDouble(idx++, f.getTrendSlope());
                stmt.setDouble(idx++, f.getTrendIntercept());
                stmt.setString(idx++, f.getTrendDirection());
                stmt.setDouble(idx++, f.getMovingAvg5());
                stmt.setDouble(idx++, f.getMovingAvg10());
                stmt.setDouble(idx++, f.getDeviationFromPredicted());
                stmt.setTimestamp(idx++, new Timestamp(f.getWindowStart()));
                stmt.setTimestamp(idx++, new Timestamp(f.getWindowEnd()));
                stmt.setTimestamp(idx++, new Timestamp(f.getTimestamp()));
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
