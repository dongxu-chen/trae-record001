package com.logplatform.service;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch.core.BulkRequest;
import co.elastic.clients.elasticsearch.core.bulk.BulkOperation;
import com.logplatform.collector.LogCollector;
import com.logplatform.model.LogEntry;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
@Service
@RequiredArgsConstructor
public class LogIngestionService {

    private final ElasticsearchClient elasticsearchClient;
    private final ObjectMapper objectMapper;
    private final List<LogCollector> collectors;
    private final RealtimeLogService realtimeLogService;
    private final LogMiningService logMiningService;

    private final BlockingQueue<LogEntry> bufferQueue = new LinkedBlockingQueue<>(10000);
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(2);
    private final AtomicInteger pendingCount = new AtomicInteger(0);
    private volatile boolean running = false;

    @PostConstruct
    public void start() {
        running = true;

        LogCollector.LogHandler handler = this::ingest;
        for (LogCollector collector : collectors) {
            try {
                java.lang.reflect.Method method = collector.getClass().getMethod("setLogHandler", LogCollector.LogHandler.class);
                method.invoke(collector, handler);
            } catch (Exception e) {
                log.warn("Could not set log handler for collector: {}", collector.getName(), e);
            }
        }

        scheduler.scheduleAtFixedRate(this::flushBatch, 1, 1, TimeUnit.SECONDS);
        log.info("LogIngestionService started");
    }

    public void ingest(LogEntry entry) {
        if (entry == null) return;

        if (entry.getTimestamp() == null) {
            entry.setTimestamp(Instant.now());
        }

        realtimeLogService.publishLog(entry);
        logMiningService.processRealtimeLog(entry);

        if (!bufferQueue.offer(entry)) {
            log.warn("Buffer queue is full, dropping log entry");
        } else {
            pendingCount.incrementAndGet();
        }

        if (pendingCount.get() >= 500) {
            flushBatch();
        }
    }

    public void ingest(List<LogEntry> entries) {
        for (LogEntry entry : entries) {
            ingest(entry);
        }
    }

    private void flushBatch() {
        if (pendingCount.get() == 0) return;

        List<LogEntry> batch = new ArrayList<>();
        bufferQueue.drainTo(batch, 500);

        if (batch.isEmpty()) return;

        try {
            String indexName = getIndexName();
            BulkRequest.Builder bulkBuilder = new BulkRequest.Builder();

            for (LogEntry entry : batch) {
                String id = UUID.randomUUID().toString();

                Map<String, Object> doc = objectMapper.convertValue(entry, Map.class);
                doc.put("@timestamp", entry.getTimestamp().toString());

                bulkBuilder.operations(BulkOperation.of(op -> op
                        .index(idx -> idx
                                .index(indexName)
                                .id(id)
                                .document(doc))));
            }

            elasticsearchClient.bulk(bulkBuilder.build());
            pendingCount.addAndGet(-batch.size());

            log.debug("Flushed {} log entries to {}", batch.size(), indexName);
        } catch (Exception e) {
            log.error("Failed to flush log batch", e);
            bufferQueue.addAll(batch);
        }
    }

    private String getIndexName() {
        return "unified-logs-" + LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy.MM.dd"));
    }

    public void stop() {
        running = false;
        flushBatch();
        scheduler.shutdown();
        log.info("LogIngestionService stopped");
    }

    public int getPendingCount() {
        return pendingCount.get();
    }
}
