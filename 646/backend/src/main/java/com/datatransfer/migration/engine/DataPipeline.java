package com.datatransfer.migration.engine;

import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Consumer;

@Slf4j
public class DataPipeline {
    private final DataSourceReader reader;
    private final DataProcessor processor;
    private final DataSourceWriter writer;
    private final int batchSize;
    private final RateLimiter rateLimiter;

    private final AtomicLong processedCount = new AtomicLong(0);
    private final AtomicLong errorCount = new AtomicLong(0);
    private final AtomicLong backupCount = new AtomicLong(0);
    private volatile boolean running = true;
    private volatile boolean rollbackTriggered = false;
    private PipelineProgressListener progressListener;
    private Consumer<List<Record>> backupHandler;

    private CheckpointInfo lastCheckpoint;

    public DataPipeline(DataSourceReader reader, DataProcessor processor, DataSourceWriter writer) {
        this(reader, processor, writer, 500, RateLimiter.unlimited(), null);
    }

    public DataPipeline(DataSourceReader reader, DataProcessor processor, DataSourceWriter writer, int batchSize,
                       RateLimiter rateLimiter, Consumer<List<Record>> backupHandler) {
        this.reader = reader;
        this.processor = processor;
        this.writer = writer;
        this.batchSize = batchSize;
        this.rateLimiter = rateLimiter != null ? rateLimiter : RateLimiter.unlimited();
        this.backupHandler = backupHandler;
    }

    public void setProgressListener(PipelineProgressListener listener) {
        this.progressListener = listener;
    }

    public void setBackupHandler(Consumer<List<Record>> backupHandler) {
        this.backupHandler = backupHandler;
    }

    public void triggerRollback() {
        this.rollbackTriggered = true;
        this.running = false;
        log.warn("Rollback triggered, stopping pipeline and will trigger rollback flow");
    }

    public void execute(Map<String, Object> config) throws Exception {
        execute(config, null);
    }

    public void execute(Map<String, Object> config, CheckpointInfo resumeCheckpoint) throws Exception {
        log.info("Starting data pipeline execution, batchSize={}, rateLimit={} records/s, resumeFrom={}",
                batchSize,
                rateLimiter.isUnlimited() ? "unlimited" : rateLimiter.getMaxRecordsPerSecond(),
                resumeCheckpoint != null ? resumeCheckpoint.getPositionValue() : "beginning");

        try {
            if (resumeCheckpoint != null) {
                reader.openFromPosition(config, resumeCheckpoint);
                processedCount.set(resumeCheckpoint.getProcessedRecords());
                log.info("Resumed from checkpoint: type={}, value={}, processed={}",
                        resumeCheckpoint.getPositionType(),
                        resumeCheckpoint.getPositionValue(),
                        resumeCheckpoint.getProcessedRecords());
            } else {
                reader.open(config);
            }

            processor.open();
            writer.open(config);

            long totalCount = reader.getTotalCount();
            long adjustedTotal = totalCount > 0 ? totalCount : Long.MAX_VALUE;
            log.info("Total records to process: {}, already processed: {}", totalCount, processedCount.get());

            List<Record> batch = new ArrayList<>(batchSize);
            long lastReportTime = System.currentTimeMillis();

            while (running && reader.hasNext()) {
                try {
                    Record record = reader.next();
                    batch.add(record);

                    if (batch.size() >= batchSize) {
                        processBatch(batch, adjustedTotal);
                        batch.clear();
                        writer.flush();

                        long now = System.currentTimeMillis();
                        if (now - lastReportTime >= 1000) {
                            notifyProgress(processedCount.get(), adjustedTotal);
                            lastReportTime = now;
                        }
                    }
                } catch (Exception e) {
                    errorCount.incrementAndGet();
                    log.error("Error processing record", e);
                    if (progressListener != null) {
                        progressListener.onError(e.getMessage());
                    }
                }
            }

            if (!batch.isEmpty()) {
                processBatch(batch, adjustedTotal);
                batch.clear();
            }

            writer.flush();
            notifyProgress(processedCount.get(), adjustedTotal);

            if (rollbackTriggered) {
                log.info("Pipeline stopped due to rollback trigger. Processed before rollback: {}", processedCount.get());
            } else {
                log.info("Pipeline completed. Processed: {}, Errors: {}, Backed up: {}",
                        processedCount.get(), errorCount.get(), backupCount.get());
            }

        } finally {
            closeResources();
        }
    }

    private void processBatch(List<Record> batch, long total) throws Exception {
        if (!rateLimiter.isUnlimited()) {
            rateLimiter.throttleBatch(batch.size());
        }

        if (backupHandler != null) {
            try {
                backupHandler.accept(batch);
                backupCount.addAndGet(batch.size());
            } catch (Exception e) {
                log.error("Error backing up batch", e);
            }
        }

        processor.processBatch(batch);
        writer.writeBatch(batch);

        processedCount.addAndGet(batch.size());
        lastCheckpoint = reader.currentCheckpoint();
    }

    private void notifyProgress(long processed, long total) {
        if (progressListener != null) {
            double progress = total > 0 ? (processed * 100.0 / total) : 0;
            progress = Math.min(progress, 100.0);
            CheckpointInfo cp = lastCheckpoint;
            progressListener.onProgress(progress, processed, total, cp, rateLimiter.getMaxRecordsPerSecond());
        }
    }

    private void closeResources() {
        try { writer.close(); } catch (Exception e) { log.error("Error closing writer", e); }
        try { processor.close(); } catch (Exception e) { log.error("Error closing processor", e); }
        try { reader.close(); } catch (Exception e) { log.error("Error closing reader", e); }
    }

    public void stop() { this.running = false; }

    public long getProcessedCount() { return processedCount.get(); }
    public long getErrorCount() { return errorCount.get(); }
    public long getBackupCount() { return backupCount.get(); }
    public CheckpointInfo getLastCheckpoint() { return lastCheckpoint; }
    public boolean isRollbackTriggered() { return rollbackTriggered; }
    public RateLimiter getRateLimiter() { return rateLimiter; }

    public interface PipelineProgressListener {
        void onProgress(double progress, long processed, long total, CheckpointInfo checkpoint, int rateLimit);
        void onError(String message);
    }
}
