package com.log.collector.sink;

import com.clickhouse.jdbc.ClickHouseConnection;
import com.clickhouse.jdbc.ClickHouseDataSource;
import com.log.collector.util.BackpressureManager;
import com.log.collector.util.IdempotentManager;
import com.log.collector.util.LatencyMonitor;
import org.apache.flume.*;
import org.apache.flume.conf.Configurable;
import org.apache.flume.sink.AbstractSink;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

public class ClickHouseSink extends AbstractSink implements Configurable {

    private static final Logger logger = LoggerFactory.getLogger(ClickHouseSink.class);

    private String jdbcUrl;
    private String username;
    private String password;
    private String database;
    private String table;
    private String[] columns;
    private int batchSize;
    private long batchTimeoutMs;
    private int maxRetries;
    private long retryIntervalMs;
    private boolean asyncWrite;
    private int asyncQueueSize;

    private ClickHouseDataSource dataSource;
    private ClickHouseConnection connection;

    private BackpressureManager backpressureManager;
    private IdempotentManager idempotentManager;
    private boolean enableIdempotent;
    private boolean enableBackpressure;
    private double backpressureThreshold;

    private ExecutorService asyncExecutor;
    private LinkedBlockingQueue<List<Event>> writeQueue;
    private final AtomicLong pendingEvents = new AtomicLong(0);
    private final AtomicLong totalWritten = new AtomicLong(0);
    private final AtomicLong totalFailed = new AtomicLong(0);

    @Override
    public void configure(Context context) {
        String host = context.getString("host", "localhost");
        int port = context.getInteger("port", 8123);
        database = context.getString("database", "default");
        table = context.getString("table", "logs");
        username = context.getString("username", "default");
        password = context.getString("password", "");

        jdbcUrl = String.format("jdbc:ch://%s:%d/%s", host, port, database);

        String columnsStr = context.getString("columns", "message");
        columns = columnsStr.split(",");
        for (int i = 0; i < columns.length; i++) {
            columns[i] = columns[i].trim();
        }

        batchSize = context.getInteger("batchSize", 1000);
        batchTimeoutMs = context.getLong("batchTimeoutMs", 30000L);
        maxRetries = context.getInteger("maxRetries", 3);
        retryIntervalMs = context.getLong("retryIntervalMs", 1000L);
        asyncWrite = context.getBoolean("asyncWrite", true);
        asyncQueueSize = context.getInteger("asyncQueueSize", 10);

        enableIdempotent = context.getBoolean("idempotent.enabled", true);
        enableBackpressure = context.getBoolean("backpressure.enabled", true);
        backpressureThreshold = context.getDouble("backpressure.threshold", 0.7);

        backpressureManager = BackpressureManager.getInstance();

        if (enableIdempotent) {
            Properties redisProps = new Properties();
            redisProps.setProperty("redis.host", context.getString("redis.host", "localhost"));
            redisProps.setProperty("redis.port", String.valueOf(context.getInteger("redis.port", 6379)));
            redisProps.setProperty("redis.password", context.getString("redis.password", ""));
            redisProps.setProperty("redis.idempotent.enabled", "true");
            idempotentManager = IdempotentManager.getInstance(redisProps);
        }

        logger.info("ClickHouseSink configured - url: {}, table: {}, batchSize: {}, async: {}, idempotent: {}",
                jdbcUrl, table, batchSize, asyncWrite, enableIdempotent);
    }

    @Override
    public synchronized void start() {
        logger.info("Starting ClickHouseSink...");
        try {
            Properties properties = new Properties();
            properties.setProperty("user", username);
            properties.setProperty("password", password);
            properties.setProperty("socket_timeout", "300000");
            properties.setProperty("use_server_time_zone", "UTC");

            dataSource = new ClickHouseDataSource(jdbcUrl, properties);
            connection = dataSource.getConnection();

            if (asyncWrite) {
                writeQueue = new LinkedBlockingQueue<>(asyncQueueSize);
                asyncExecutor = Executors.newSingleThreadExecutor();
                asyncExecutor.submit(this::asyncWriteWorker);
            }

            logger.info("ClickHouseSink started successfully");
        } catch (Exception e) {
            logger.error("Failed to start ClickHouseSink", e);
            throw new FlumeException("Failed to connect to ClickHouse", e);
        }
        super.start();
    }

    @Override
    public Status process() throws EventDeliveryException {
        Channel channel = getChannel();
        Transaction transaction = channel.getTransaction();
        List<Event> events = new ArrayList<>();

        try {
            transaction.begin();

            long startTime = System.currentTimeMillis();

            for (int i = 0; i < batchSize; i++) {
                Event event = channel.take();
                if (event == null) {
                    break;
                }
                events.add(event);

                long elapsed = System.currentTimeMillis() - startTime;
                if (elapsed >= batchTimeoutMs) {
                    break;
                }
            }

            if (events.isEmpty()) {
                transaction.commit();
                return Status.BACKOFF;
            }

            List<Event> filteredEvents = filterDuplicates(events);

            if (filteredEvents.isEmpty()) {
                transaction.commit();
                return Status.READY;
            }

            if (enableBackpressure) {
                checkAndTriggerBackpressure(filteredEvents.size());
            }

            if (asyncWrite) {
                boolean queued = writeQueue.offer(filteredEvents, 5, TimeUnit.SECONDS);
                if (!queued) {
                    transaction.rollback();
                    logger.warn("Write queue full, triggering backpressure");
                    backpressureManager.triggerBackpressure();
                    return Status.BACKOFF;
                }
                pendingEvents.addAndGet(filteredEvents.size());
            } else {
                executeWithRetry(filteredEvents);
                markProcessed(filteredEvents);
                totalWritten.addAndGet(filteredEvents.size());
            }

            transaction.commit();
            logger.debug("Processed {} events to ClickHouse", filteredEvents.size());
            return Status.READY;

        } catch (Exception e) {
            transaction.rollback();
            totalFailed.addAndGet(events.size());
            logger.error("Failed to process events, sending to DLQ", e);
            sendToDeadLetterQueue(events, e);
            throw new EventDeliveryException("Failed to write to ClickHouse", e);
        } finally {
            transaction.close();
        }
    }

    private List<Event> filterDuplicates(List<Event> events) {
        if (!enableIdempotent) {
            return events;
        }

        List<Event> filtered = new ArrayList<>();
        for (Event event : events) {
            String idempotentId = event.getHeaders().get("idempotent_id");
            if (idempotentId == null) {
                idempotentId = idempotentManager.generateIdempotentId(event);
            }

            if (!idempotentManager.isProcessed(idempotentId)) {
                filtered.add(event);
            } else {
                logger.debug("Duplicate event filtered: {}", idempotentId);
            }
        }
        return filtered;
    }

    private void markProcessed(List<Event> events) {
        if (!enableIdempotent) {
            return;
        }

        for (Event event : events) {
            String idempotentId = event.getHeaders().get("idempotent_id");
            if (idempotentId != null) {
                idempotentManager.markProcessedAsync(idempotentId);
            }
        }
    }

    private void checkAndTriggerBackpressure(int eventCount) {
        double queueUsage = (double) pendingEvents.get() / (asyncQueueSize * batchSize);
        if (queueUsage >= backpressureThreshold) {
            if (!backpressureManager.isBackpressureActive()) {
                logger.warn("ClickHouse queue usage {}%, triggering backpressure",
                        (int)(queueUsage * 100));
                backpressureManager.triggerBackpressure();
            }
        } else if (queueUsage <= backpressureThreshold * 0.5) {
            if (backpressureManager.isBackpressureActive()) {
                logger.info("ClickHouse queue usage {}%, releasing backpressure",
                        (int)(queueUsage * 100));
                backpressureManager.releaseBackpressure();
            }
        }
    }

    private void asyncWriteWorker() {
        logger.info("Async write worker started");

        while (!Thread.currentThread().isInterrupted()) {
            try {
                List<Event> events = writeQueue.poll(1, TimeUnit.SECONDS);
                if (events == null) {
                    continue;
                }

                try {
                    executeWithRetry(events);
                    markProcessed(events);
                    totalWritten.addAndGet(events.size());
                    pendingEvents.addAndGet(-events.size());

                    if (enableBackpressure) {
                        checkAndTriggerBackpressure(0);
                    }

                } catch (Exception e) {
                    totalFailed.addAndGet(events.size());
                    pendingEvents.addAndGet(-events.size());
                    logger.error("Async write failed, sending to DLQ", e);
                    sendToDeadLetterQueue(events, e);
                }

            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            } catch (Exception e) {
                logger.error("Error in async write worker", e);
            }
        }

        logger.info("Async write worker stopped");
    }

    private void executeWithRetry(List<Event> events) throws Exception {
        int retryCount = 0;
        Exception lastException = null;

        while (retryCount < maxRetries) {
            try {
                executeBatchInsert(events);
                return;
            } catch (Exception e) {
                lastException = e;
                retryCount++;
                logger.warn("Batch insert failed (attempt {}/{}): {}",
                        retryCount, maxRetries, e.getMessage());

                if (retryCount < maxRetries) {
                    reconnect();
                    TimeUnit.MILLISECONDS.sleep(retryIntervalMs * retryCount);
                }
            }
        }

        throw lastException;
    }

    private void executeBatchInsert(List<Event> events) throws SQLException {
        String sql = buildInsertSQL();
        long ingestTimestamp = System.currentTimeMillis();

        try (PreparedStatement stmt = connection.prepareStatement(sql)) {
            for (Event event : events) {
                Map<String, String> headers = event.getHeaders();
                String body = new String(event.getBody());

                for (int i = 0; i < columns.length; i++) {
                    String column = columns[i];
                    String value;

                    if ("body".equalsIgnoreCase(column)) {
                        value = body;
                    } else {
                        value = headers.getOrDefault(column, "");
                    }

                    stmt.setString(i + 1, value);
                }
                stmt.addBatch();

                String produceTimestampStr = headers.get("timestamp");
                if (produceTimestampStr == null) {
                    produceTimestampStr = headers.get("log_timestamp");
                }
                if (produceTimestampStr == null) {
                    produceTimestampStr = headers.get("@timestamp");
                }

                if (produceTimestampStr != null) {
                    try {
                        long produceTimestamp = Long.parseLong(produceTimestampStr);
                        String level = headers.get("log_level");
                        LatencyMonitor.getInstance().recordLatency(produceTimestamp, ingestTimestamp, level);
                    } catch (NumberFormatException e) {
                    }
                }
            }

            int[] results = stmt.executeBatch();
            int successCount = 0;
            for (int result : results) {
                if (result > 0 || result == PreparedStatement.SUCCESS_NO_INFO) {
                    successCount++;
                }
            }

            if (successCount != events.size()) {
                logger.warn("Batch insert completed with partial success: {}/{}",
                        successCount, events.size());
            }
        }
    }

    private String buildInsertSQL() {
        StringBuilder sql = new StringBuilder("INSERT INTO ");
        sql.append(table).append(" (");

        for (int i = 0; i < columns.length; i++) {
            if (i > 0) sql.append(", ");
            sql.append(columns[i]);
        }

        sql.append(") VALUES (");

        for (int i = 0; i < columns.length; i++) {
            if (i > 0) sql.append(", ");
            sql.append("?");
        }

        sql.append(")");
        return sql.toString();
    }

    private void reconnect() {
        try {
            if (connection != null && !connection.isClosed()) {
                connection.close();
            }
        } catch (SQLException e) {
            logger.warn("Error closing existing connection", e);
        }

        try {
            connection = dataSource.getConnection();
            logger.info("Reconnected to ClickHouse");
        } catch (SQLException e) {
            logger.error("Failed to reconnect to ClickHouse", e);
        }
    }

    private void sendToDeadLetterQueue(List<Event> events, Exception e) {
        for (Event event : events) {
            event.getHeaders().put("dlq_reason", e.getMessage());
            event.getHeaders().put("dlq_timestamp", String.valueOf(System.currentTimeMillis()));
            event.getHeaders().put("dlq_sink", "clickhouse");
        }
    }

    @Override
    public synchronized void stop() {
        logger.info("Stopping ClickHouseSink...");

        if (asyncExecutor != null) {
            asyncExecutor.shutdown();
            try {
                if (!asyncExecutor.awaitTermination(30, TimeUnit.SECONDS)) {
                    asyncExecutor.shutdownNow();
                }
            } catch (InterruptedException e) {
                asyncExecutor.shutdownNow();
            }
        }

        while (writeQueue != null && !writeQueue.isEmpty()) {
            List<Event> events = writeQueue.poll();
            if (events != null) {
                try {
                    executeWithRetry(events);
                } catch (Exception e) {
                    logger.error("Failed to flush pending events", e);
                }
            }
        }

        try {
            if (connection != null && !connection.isClosed()) {
                connection.close();
            }
        } catch (SQLException e) {
            logger.warn("Error closing ClickHouse connection", e);
        }

        logger.info("ClickHouseSink stopped - written: {}, failed: {}",
                totalWritten.get(), totalFailed.get());
        super.stop();
    }
}
