package com.datatransfer.migration.engine;

import com.datatransfer.migration.adapter.DataSourceAdapter;
import com.datatransfer.migration.adapter.DataSourceAdapterFactory;
import com.datatransfer.migration.model.Checkpoint;
import com.datatransfer.migration.model.DataSource;
import com.datatransfer.migration.model.RollbackRecord;
import com.datatransfer.migration.model.Task;
import com.datatransfer.migration.model.TaskLog;
import com.datatransfer.migration.model.TaskProgress;
import com.datatransfer.migration.repository.CheckpointRepository;
import com.datatransfer.migration.repository.DataSourceRepository;
import com.datatransfer.migration.repository.TaskLogRepository;
import com.datatransfer.migration.repository.TaskProgressRepository;
import com.datatransfer.migration.repository.TaskRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class TaskExecutor {
    private final DataSourceRepository dataSourceRepository;
    private final TaskRepository taskRepository;
    private final TaskProgressRepository taskProgressRepository;
    private final TaskLogRepository taskLogRepository;
    private final CheckpointRepository checkpointRepository;
    private final DataSourceAdapterFactory adapterFactory;
    private final SimpMessagingTemplate messagingTemplate;
    private final MigrationPreValidator preValidator;
    private final RollbackExecutor rollbackExecutor;

    private final Map<Long, DataPipeline> runningPipelines = new ConcurrentHashMap<>();
    private final Map<Long, PipelineSnapshot> latestSnapshots = new ConcurrentHashMap<>();

    public TaskExecutor(DataSourceRepository dataSourceRepository,
                        TaskRepository taskRepository,
                        TaskProgressRepository taskProgressRepository,
                        TaskLogRepository taskLogRepository,
                        CheckpointRepository checkpointRepository,
                        DataSourceAdapterFactory adapterFactory,
                        SimpMessagingTemplate messagingTemplate,
                        MigrationPreValidator preValidator,
                        RollbackExecutor rollbackExecutor) {
        this.dataSourceRepository = dataSourceRepository;
        this.taskRepository = taskRepository;
        this.taskProgressRepository = taskProgressRepository;
        this.taskLogRepository = taskLogRepository;
        this.checkpointRepository = checkpointRepository;
        this.adapterFactory = adapterFactory;
        this.messagingTemplate = messagingTemplate;
        this.preValidator = preValidator;
        this.rollbackExecutor = rollbackExecutor;
    }

    public MigrationPreValidator.ValidationResult preValidate(Long taskId) {
        Task task = taskRepository.selectById(taskId);
        if (task == null) {
            throw new RuntimeException("Task not found: " + taskId);
        }

        DataSource sourceDs = dataSourceRepository.selectById(task.getSourceId());
        DataSource targetDs = dataSourceRepository.selectById(task.getTargetId());

        if (sourceDs == null || targetDs == null) {
            throw new RuntimeException("Source or target data source not found");
        }

        DataSourceAdapter sourceAdapter = adapterFactory.createAdapter(sourceDs);
        DataSourceAdapter targetAdapter = adapterFactory.createAdapter(targetDs);

        Map<String, Object> config = buildPipelineConfig(task);
        String sourceTable = (String) config.get("tableName");
        String targetTable = config.get("targetTableName") != null ? (String) config.get("targetTableName") : sourceTable;

        MigrationPreValidator.ValidationContext ctx = new MigrationPreValidator.ValidationContext();
        ctx.setSourceAdapter(sourceAdapter);
        ctx.setTargetAdapter(targetAdapter);
        ctx.setSourceTableName(sourceTable);
        ctx.setTargetTableName(targetTable);

        addLog(taskId, "INFO", "Starting pre-validation...");
        MigrationPreValidator.ValidationResult result = preValidator.validate(ctx);
        addLog(taskId, "INFO", "Pre-validation completed: " + result.getSummary());

        return result;
    }

    @Async
    public void executeTask(Task task) {
        log.info("Starting task execution: {}", task.getName());

        try {
            addLog(task.getId(), "INFO", "Task execution started");

            DataSource sourceDs = dataSourceRepository.selectById(task.getSourceId());
            DataSource targetDs = dataSourceRepository.selectById(task.getTargetId());
            if (sourceDs == null || targetDs == null) {
                throw new RuntimeException("Source or target data source not found");
            }

            DataSourceAdapter sourceAdapter = adapterFactory.createAdapter(sourceDs);
            DataSourceAdapter targetAdapter = adapterFactory.createAdapter(targetDs);

            MigrationPreValidator.ValidationResult validationResult = preValidate(task.getId());
            if (!validationResult.isValid()) {
                addLog(task.getId(), "ERROR", "Pre-validation failed: " + validationResult.getSummary());
                task.setStatus("failed");
                task.setFinishedAt(LocalDateTime.now());
                taskRepository.updateById(task);
                return;
            }
            addLog(task.getId(), "INFO", "Pre-validation passed");

            Map<String, Object> config = buildPipelineConfig(task);
            CheckpointInfo resumeCheckpoint = loadLastCheckpoint(task.getId());

            boolean enableBackup = config.get("enableBackup") != null && (Boolean) config.get("enableBackup");
            String rollbackStrategy = config.get("rollbackStrategy") != null ? (String) config.get("rollbackStrategy") : "table_restore";
            String targetTableName = config.get("targetTableName") != null ? (String) config.get("targetTableName") : (String) config.get("tableName");

            RollbackRecord backupRecord = null;
            if (enableBackup && resumeCheckpoint == null) {
                addLog(task.getId(), "INFO", "Creating backup before migration...");
                backupRecord = rollbackExecutor.createBackup(task.getId(), targetAdapter, targetTableName, rollbackStrategy);
                addLog(task.getId(), "INFO", String.format("Backup created: %s, %d records",
                        backupRecord.getBackupTableName(), backupRecord.getBackupRecords()));
            }

            DataSourceReader reader = sourceAdapter.createReader();
            DataSourceWriter writer = targetAdapter.createWriter();
            DataProcessor processor = buildProcessorChain(task);

            int batchSize = config.get("batchSize") != null ? ((Number) config.get("batchSize")).intValue() : 500;
            int rateLimit = config.get("rateLimit") != null ? ((Number) config.get("rateLimit")).intValue() : 0;
            RateLimiter rateLimiter = rateLimit > 0 ? new RateLimiter(rateLimit) : RateLimiter.unlimited();

            addLog(task.getId(), "INFO", String.format("Pipeline configured: batchSize=%d, rateLimit=%s records/s",
                    batchSize, rateLimiter.isUnlimited() ? "unlimited" : String.valueOf(rateLimit)));

            DataPipeline pipeline = new DataPipeline(reader, processor, writer, batchSize, rateLimiter, null);
            runningPipelines.put(task.getId(), pipeline);

            task.setStatus("running");
            task.setStartedAt(LocalDateTime.now());
            taskRepository.updateById(task);

            final RollbackRecord finalBackupRecord = backupRecord;
            pipeline.setProgressListener(new DataPipeline.PipelineProgressListener() {
                private long lastUpdate = System.currentTimeMillis();
                private long lastProcessed = resumeCheckpoint != null ? resumeCheckpoint.getProcessedRecords() : 0;

                @Override
                public void onProgress(double progress, long processed, long total, CheckpointInfo checkpoint, int rateLimit) {
                    long now = System.currentTimeMillis();
                    long elapsed = now - lastUpdate;
                    double throughput = 0;
                    if (elapsed > 0) {
                        throughput = (processed - lastProcessed) / (elapsed / 1000.0);
                    }

                    PipelineSnapshot snapshot = new PipelineSnapshot();
                    snapshot.setProgress(progress);
                    snapshot.setProcessedRecords(processed);
                    snapshot.setTotalRecords(total);
                    snapshot.setThroughput(throughput);
                    snapshot.setBatchSize(batchSize);
                    snapshot.setRateLimit(rateLimit);
                    if (checkpoint != null) {
                        snapshot.setPositionType(checkpoint.getPositionType());
                        snapshot.setPositionValue(checkpoint.getPositionValue());
                    }
                    latestSnapshots.put(task.getId(), snapshot);

                    updateProgress(task.getId(), progress, processed, total, 0, throughput, checkpoint, batchSize, rateLimit);
                    saveCheckpoint(task.getId(), checkpoint, config);
                    sendProgressWebSocket(task.getId(), progress, processed, total, throughput, checkpoint, batchSize, rateLimit);

                    lastUpdate = now;
                    lastProcessed = processed;
                }

                @Override
                public void onError(String message) {
                    addLog(task.getId(), "ERROR", message);
                }
            });

            boolean autoRollback = config.get("autoRollback") != null && (Boolean) config.get("autoRollback");
            try {
                pipeline.execute(config, resumeCheckpoint);

                if (pipeline.isRollbackTriggered()) {
                    task.setStatus("rollback");
                    taskRepository.updateById(task);
                    addLog(task.getId(), "WARN", "Pipeline stopped, triggering rollback...");
                    if (finalBackupRecord != null) {
                        rollbackExecutor.executeRollback(task.getId(), targetAdapter, finalBackupRecord);
                        task.setStatus("rollback_completed");
                    } else {
                        addLog(task.getId(), "WARN", "No backup available for rollback");
                        task.setStatus("failed");
                    }
                } else {
                    task.setStatus("completed");
                }
                task.setFinishedAt(LocalDateTime.now());
                taskRepository.updateById(task);
                addLog(task.getId(), "INFO", "Task completed successfully, processed: " + pipeline.getProcessedCount());

            } catch (Exception e) {
                log.error("Task execution failed", e);
                task.setStatus("failed");
                task.setFinishedAt(LocalDateTime.now());
                taskRepository.updateById(task);
                addLog(task.getId(), "ERROR", "Task failed: " + e.getMessage());

                if (autoRollback && finalBackupRecord != null) {
                    addLog(task.getId(), "WARN", "Auto-rollback triggered due to failure...");
                    task.setStatus("rollback");
                    taskRepository.updateById(task);
                    rollbackExecutor.executeRollback(task.getId(), targetAdapter, finalBackupRecord);
                    task.setStatus("rollback_completed");
                    taskRepository.updateById(task);
                    addLog(task.getId(), "INFO", "Auto-rollback completed");
                }
            }

        } catch (Exception e) {
            log.error("Task execution setup failed", e);
            Task t = taskRepository.selectById(task.getId());
            if (t != null) {
                t.setStatus("failed");
                t.setFinishedAt(LocalDateTime.now());
                taskRepository.updateById(t);
            }
            addLog(task.getId(), "ERROR", "Task failed: " + e.getMessage());
        } finally {
            runningPipelines.remove(task.getId());
            latestSnapshots.remove(task.getId());
        }
    }

    public void stopTask(Long taskId) {
        DataPipeline pipeline = runningPipelines.get(taskId);
        if (pipeline != null) {
            pipeline.stop();
            CheckpointInfo cp = pipeline.getLastCheckpoint();
            if (cp != null) {
                addLog(taskId, "INFO", "Task paused at checkpoint: " + cp.getPositionType() + "=" + cp.getPositionValue());
            } else {
                addLog(taskId, "INFO", "Task stopped by user");
            }
        }
    }

    public void triggerRollback(Long taskId) {
        DataPipeline pipeline = runningPipelines.get(taskId);
        if (pipeline != null) {
            pipeline.triggerRollback();
            addLog(taskId, "WARN", "Rollback triggered by user");
        }
    }

    public PipelineSnapshot getLatestSnapshot(Long taskId) {
        return latestSnapshots.get(taskId);
    }

    private CheckpointInfo loadLastCheckpoint(Long taskId) {
        com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<Checkpoint> wrapper =
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<>();
        wrapper.eq(Checkpoint::getTaskId, taskId)
                .orderByDesc(Checkpoint::getUpdatedAt)
                .last("LIMIT 1");
        Checkpoint cp = checkpointRepository.selectOne(wrapper);
        if (cp == null) return null;

        CheckpointInfo info = new CheckpointInfo();
        info.setPositionType(cp.getPositionType());
        info.setPositionValue(cp.getPositionValue());
        info.setProcessedRecords(cp.getProcessedRecords() != null ? cp.getProcessedRecords() : 0);
        log.info("Loaded checkpoint for task {}: type={}, value={}, processed={}",
                taskId, cp.getPositionType(), cp.getPositionValue(), cp.getProcessedRecords());
        return info;
    }

    private void saveCheckpoint(Long taskId, CheckpointInfo checkpoint, Map<String, Object> config) {
        if (checkpoint == null) return;
        Checkpoint cp = new Checkpoint();
        cp.setTaskId(taskId);
        cp.setTableName((String) config.get("tableName"));
        cp.setPositionType(checkpoint.getPositionType());
        cp.setPositionValue(checkpoint.getPositionValue());
        cp.setProcessedRecords(checkpoint.getProcessedRecords());
        cp.setCreatedAt(LocalDateTime.now());
        cp.setUpdatedAt(LocalDateTime.now());
        checkpointRepository.insert(cp);
    }

    private Map<String, Object> buildPipelineConfig(Task task) {
        Map<String, Object> config = new HashMap<>();
        Map<String, Object> taskConfig = task.getConfig();
        if (taskConfig != null) {
            config.putAll(taskConfig);
        }
        return config;
    }

    private DataProcessor buildProcessorChain(Task task) {
        DataProcessor processor = record -> {};
        Map<String, Object> config = task.getConfig();
        if (config == null) return processor;

        @SuppressWarnings("unchecked")
        List<Map<String, String>> maskingRules = (List<Map<String, String>>) config.get("maskingRules");
        if (maskingRules != null && !maskingRules.isEmpty()) {
            processor = processor.andThen(new MaskingProcessor(maskingRules));
        }

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> transformRules = (List<Map<String, Object>>) config.get("transformRules");
        if (transformRules != null && !transformRules.isEmpty()) {
            processor = processor.andThen(new TransformProcessor(transformRules));
        }

        return processor;
    }

    private void updateProgress(Long taskId, double progress, long processed, long total, long errors,
                                 double throughput, CheckpointInfo checkpoint, int batchSize, int rateLimit) {
        TaskProgress tp = new TaskProgress();
        tp.setTaskId(taskId);
        tp.setProgress(Math.min(progress, 100.0));
        tp.setProcessedRecords(processed);
        tp.setTotalRecords(total);
        tp.setErrorRecords(errors);
        tp.setThroughput(throughput);
        tp.setBatchSize((long) batchSize);
        if (checkpoint != null) {
            tp.setCurrentPositionType(checkpoint.getPositionType());
            tp.setCurrentPositionValue(checkpoint.getPositionValue());
        }
        tp.setUpdatedAt(LocalDateTime.now());
        taskProgressRepository.insert(tp);
    }

    private void sendProgressWebSocket(Long taskId, double progress, long processed, long total,
                                        double throughput, CheckpointInfo checkpoint, int batchSize, int rateLimit) {
        Map<String, Object> message = new HashMap<>();
        message.put("taskId", taskId);
        message.put("progress", progress);
        message.put("processedRecords", processed);
        message.put("totalRecords", total);
        message.put("throughput", throughput);
        message.put("batchSize", batchSize);
        message.put("rateLimit", rateLimit);
        if (checkpoint != null) {
            message.put("positionType", checkpoint.getPositionType());
            message.put("positionValue", checkpoint.getPositionValue());
        }
        messagingTemplate.convertAndSend("/topic/tasks/" + taskId + "/progress", message);
    }

    private void addLog(Long taskId, String level, String message) {
        TaskLog logEntry = new TaskLog();
        logEntry.setTaskId(taskId);
        logEntry.setLevel(level);
        logEntry.setMessage(message);
        logEntry.setCreatedAt(LocalDateTime.now());
        taskLogRepository.insert(logEntry);

        Map<String, Object> wsMessage = new HashMap<>();
        wsMessage.put("level", level);
        wsMessage.put("message", message);
        wsMessage.put("timestamp", LocalDateTime.now().toString());
        messagingTemplate.convertAndSend("/topic/tasks/" + taskId + "/logs", wsMessage);
    }

    public static class PipelineSnapshot {
        private double progress;
        private long processedRecords;
        private long totalRecords;
        private double throughput;
        private String positionType;
        private String positionValue;
        private int batchSize;
        private int rateLimit;

        public double getProgress() { return progress; }
        public void setProgress(double progress) { this.progress = progress; }
        public long getProcessedRecords() { return processedRecords; }
        public void setProcessedRecords(long processedRecords) { this.processedRecords = processedRecords; }
        public long getTotalRecords() { return totalRecords; }
        public void setTotalRecords(long totalRecords) { this.totalRecords = totalRecords; }
        public double getThroughput() { return throughput; }
        public void setThroughput(double throughput) { this.throughput = throughput; }
        public String getPositionType() { return positionType; }
        public void setPositionType(String positionType) { this.positionType = positionType; }
        public String getPositionValue() { return positionValue; }
        public void setPositionValue(String positionValue) { this.positionValue = positionValue; }
        public int getBatchSize() { return batchSize; }
        public void setBatchSize(int batchSize) { this.batchSize = batchSize; }
        public int getRateLimit() { return rateLimit; }
        public void setRateLimit(int rateLimit) { this.rateLimit = rateLimit; }
    }
}
