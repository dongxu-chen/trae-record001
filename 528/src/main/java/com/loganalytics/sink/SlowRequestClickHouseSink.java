package com.loganalytics.sink;

import com.loganalytics.config.FlinkConfig;
import com.loganalytics.model.SlowRequestEvent;
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

public class SlowRequestClickHouseSink extends RichSinkFunction<SlowRequestEvent> {

    private static final Logger LOG = LoggerFactory.getLogger(SlowRequestClickHouseSink.class);

    private final FlinkConfig config;
    private final int batchSize;
    private final long flushIntervalMs;

    private transient Connection connection;
    private transient List<SlowRequestEvent> batch;
    private transient ReentrantLock lock;
    private transient ScheduledExecutorService scheduler;

    public SlowRequestClickHouseSink(FlinkConfig config) {
        this(config, 500, 5000);
    }

    public SlowRequestClickHouseSink(FlinkConfig config, int batchSize, long flushIntervalMs) {
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
    public void invoke(SlowRequestEvent event, Context context) throws Exception {
        lock.lock();
        try {
            batch.add(event);
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
            LOG.error("Failed to flush slow request batch", e);
        } finally {
            lock.unlock();
        }
    }

    private void flushBatch() throws Exception {
        if (batch.isEmpty()) {
            return;
        }

        String sql = "INSERT INTO slow_requests (" +
                "trace_id, dimension, value, method, path, uri, status, " +
                "request_time, upstream_response_time, self_process_time, " +
                "remote_addr, host, upstream_status, " +
                "is_upstream_slow, is_self_slow, slow_reason, downstream_spans, timestamp" +
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

        try (PreparedStatement stmt = connection.prepareStatement(sql)) {
            for (SlowRequestEvent event : batch) {
                int idx = 1;
                stmt.setString(idx++, event.getTraceId());
                stmt.setString(idx++, event.getDimension());
                stmt.setString(idx++, event.getValue());
                stmt.setString(idx++, event.getMethod());
                stmt.setString(idx++, event.getPath());
                stmt.setString(idx++, event.getUri());
                stmt.setInt(idx++, event.getStatus());
                stmt.setDouble(idx++, event.getRequestTime());
                stmt.setDouble(idx++, event.getUpstreamResponseTime());
                stmt.setDouble(idx++, event.getSelfProcessTime());
                stmt.setString(idx++, event.getRemoteAddr());
                stmt.setString(idx++, event.getHost());
                stmt.setString(idx++, event.getUpstreamStatus());
                stmt.setInt(idx++, event.isUpstreamSlow() ? 1 : 0);
                stmt.setInt(idx++, event.isSelfSlow() ? 1 : 0);
                stmt.setString(idx++, event.getSlowReason());

                StringBuilder spansStr = new StringBuilder();
                if (event.getDownstreamSpans() != null) {
                    for (int i = 0; i < event.getDownstreamSpans().size(); i++) {
                        if (i > 0) spansStr.append(";");
                        var span = event.getDownstreamSpans().get(i);
                        spansStr.append(span.getServiceName()).append("|")
                                .append(span.getOperation()).append("|")
                                .append(span.getDuration()).append("|")
                                .append(span.getStatus());
                    }
                }
                stmt.setString(idx++, spansStr.toString());
                stmt.setTimestamp(idx++, new Timestamp(event.getTimestamp()));
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
