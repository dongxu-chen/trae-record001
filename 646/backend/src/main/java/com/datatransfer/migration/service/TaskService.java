package com.datatransfer.migration.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.datatransfer.migration.adapter.DataSourceAdapter;
import com.datatransfer.migration.adapter.DataSourceAdapterFactory;
import com.datatransfer.migration.engine.MigrationPreValidator;
import com.datatransfer.migration.engine.RollbackExecutor;
import com.datatransfer.migration.engine.TaskExecutor;
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
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class TaskService {
    private final TaskRepository taskRepository;
    private final TaskProgressRepository taskProgressRepository;
    private final TaskLogRepository taskLogRepository;
    private final CheckpointRepository checkpointRepository;
    private final DataSourceRepository dataSourceRepository;
    private final DataSourceAdapterFactory adapterFactory;
    private final TaskExecutor taskExecutor;
    private final RollbackExecutor rollbackExecutor;

    public TaskService(TaskRepository taskRepository,
                       TaskProgressRepository taskProgressRepository,
                       TaskLogRepository taskLogRepository,
                       CheckpointRepository checkpointRepository,
                       DataSourceRepository dataSourceRepository,
                       DataSourceAdapterFactory adapterFactory,
                       TaskExecutor taskExecutor,
                       RollbackExecutor rollbackExecutor) {
        this.taskRepository = taskRepository;
        this.taskProgressRepository = taskProgressRepository;
        this.taskLogRepository = taskLogRepository;
        this.checkpointRepository = checkpointRepository;
        this.dataSourceRepository = dataSourceRepository;
        this.adapterFactory = adapterFactory;
        this.taskExecutor = taskExecutor;
        this.rollbackExecutor = rollbackExecutor;
    }

    public Page<Task> list(int page, int size, String status) {
        LambdaQueryWrapper<Task> wrapper = new LambdaQueryWrapper<>();
        if (status != null && !status.isEmpty()) {
            wrapper.eq(Task::getStatus, status);
        }
        wrapper.orderByDesc(Task::getCreatedAt);
        return taskRepository.selectPage(new Page<>(page, size), wrapper);
    }

    public Task getById(Long id) {
        return taskRepository.selectById(id);
    }

    public Task create(Task task) {
        task.setCreatedAt(LocalDateTime.now());
        task.setStatus("pending");
        task.setCreatorId(1L);
        taskRepository.insert(task);
        return task;
    }

    public Task update(Long id, Task task) {
        task.setId(id);
        taskRepository.updateById(task);
        return task;
    }

    public boolean delete(Long id) {
        return taskRepository.deleteById(id) > 0;
    }

    public MigrationPreValidator.ValidationResult preValidate(Long id) {
        return taskExecutor.preValidate(id);
    }

    public Map<String, Object> start(Long id) {
        Map<String, Object> result = new HashMap<>();
        Task task = taskRepository.selectById(id);
        if (task == null) {
            result.put("success", false);
            result.put("message", "Task not found");
            return result;
        }

        if ("running".equals(task.getStatus())) {
            result.put("success", false);
            result.put("message", "Task is already running");
            return result;
        }

        if ("paused".equals(task.getStatus())) {
            Checkpoint lastCp = getLastCheckpointEntity(id);
            if (lastCp != null) {
                result.put("resumeFromCheckpoint", Map.of(
                    "positionType", lastCp.getPositionType(),
                    "positionValue", lastCp.getPositionValue(),
                    "processedRecords", lastCp.getProcessedRecords()
                ));
            }
        }

        taskExecutor.executeTask(task);
        result.put("success", true);
        result.put("message", "Task started");
        return result;
    }

    public Map<String, Object> pause(Long id) {
        Map<String, Object> result = new HashMap<>();
        taskExecutor.stopTask(id);

        Task task = taskRepository.selectById(id);
        if (task != null) {
            task.setStatus("paused");
            taskRepository.updateById(task);
        }

        TaskExecutor.PipelineSnapshot snapshot = taskExecutor.getLatestSnapshot(id);
        if (snapshot != null) {
            result.put("checkpoint", Map.of(
                "positionType", snapshot.getPositionType() != null ? snapshot.getPositionType() : "",
                "positionValue", snapshot.getPositionValue() != null ? snapshot.getPositionValue() : "",
                "processedRecords", snapshot.getProcessedRecords()
            ));
        }

        result.put("success", true);
        result.put("message", "Task paused");
        return result;
    }

    public Map<String, Object> rollback(Long id) {
        Map<String, Object> result = new HashMap<>();
        Task task = taskRepository.selectById(id);
        if (task == null) {
            result.put("success", false);
            result.put("message", "Task not found");
            return result;
        }

        RollbackRecord backupRecord = rollbackExecutor.getLatestRollbackRecord(id);
        if (backupRecord == null || !"BACKUP_COMPLETED".equals(backupRecord.getRollbackStatus())) {
            result.put("success", false);
            result.put("message", "No valid backup available for rollback");
            return result;
        }

        taskExecutor.triggerRollback(id);

        try {
            DataSource targetDs = dataSourceRepository.selectById(task.getTargetId());
            DataSourceAdapter targetAdapter = adapterFactory.createAdapter(targetDs);
            rollbackExecutor.executeRollback(id, targetAdapter, backupRecord);
            result.put("success", true);
            result.put("message", "Rollback initiated");
            result.put("backupTableName", backupRecord.getBackupTableName());
        } catch (Exception e) {
            result.put("success", false);
            result.put("message", "Rollback initiation failed: " + e.getMessage());
        }

        return result;
    }

    public Map<String, Object> getRollbackStatus(Long id) {
        return rollbackExecutor.getRollbackStatus(id);
    }

    public Map<String, Object> getStatus(Long id) {
        Map<String, Object> result = new HashMap<>();
        Task task = taskRepository.selectById(id);
        if (task == null) {
            result.put("success", false);
            return result;
        }

        result.put("id", task.getId());
        result.put("name", task.getName());
        result.put("status", task.getStatus());
        result.put("progress", 0);

        LambdaQueryWrapper<TaskProgress> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(TaskProgress::getTaskId, id)
                .orderByDesc(TaskProgress::getUpdatedAt)
                .last("LIMIT 1");
        TaskProgress progress = taskProgressRepository.selectOne(wrapper);
        if (progress != null) {
            result.put("progress", progress.getProgress());
            result.put("processedRecords", progress.getProcessedRecords());
            result.put("totalRecords", progress.getTotalRecords());
            result.put("errorRecords", progress.getErrorRecords());
            result.put("throughput", progress.getThroughput());
            result.put("batchSize", progress.getBatchSize());
            result.put("positionType", progress.getCurrentPositionType());
            result.put("positionValue", progress.getCurrentPositionValue());
        }

        TaskExecutor.PipelineSnapshot snapshot = taskExecutor.getLatestSnapshot(id);
        if (snapshot != null) {
            result.put("liveProgress", snapshot.getProgress());
            result.put("liveProcessedRecords", snapshot.getProcessedRecords());
            result.put("liveThroughput", snapshot.getThroughput());
            result.put("livePositionType", snapshot.getPositionType());
            result.put("livePositionValue", snapshot.getPositionValue());
            result.put("liveBatchSize", snapshot.getBatchSize());
            result.put("liveRateLimit", snapshot.getRateLimit());
        }

        Map<String, Object> rollbackStatus = rollbackExecutor.getRollbackStatus(id);
        if (Boolean.TRUE.equals(rollbackStatus.get("success"))) {
            result.put("rollbackStatus", rollbackStatus);
        }

        return result;
    }

    public Map<String, Object> getRealtimePosition(Long id) {
        Map<String, Object> result = new HashMap<>();
        TaskExecutor.PipelineSnapshot snapshot = taskExecutor.getLatestSnapshot(id);
        if (snapshot != null) {
            result.put("success", true);
            result.put("progress", snapshot.getProgress());
            result.put("processedRecords", snapshot.getProcessedRecords());
            result.put("totalRecords", snapshot.getTotalRecords());
            result.put("throughput", snapshot.getThroughput());
            result.put("batchSize", snapshot.getBatchSize());
            result.put("rateLimit", snapshot.getRateLimit());
            result.put("positionType", snapshot.getPositionType());
            result.put("positionValue", snapshot.getPositionValue());
        } else {
            LambdaQueryWrapper<TaskProgress> wrapper = new LambdaQueryWrapper<>();
            wrapper.eq(TaskProgress::getTaskId, id)
                    .orderByDesc(TaskProgress::getUpdatedAt)
                    .last("LIMIT 1");
            TaskProgress progress = taskProgressRepository.selectOne(wrapper);
            if (progress != null) {
                result.put("success", true);
                result.put("progress", progress.getProgress());
                result.put("processedRecords", progress.getProcessedRecords());
                result.put("totalRecords", progress.getTotalRecords());
                result.put("throughput", progress.getThroughput());
                result.put("batchSize", progress.getBatchSize());
                result.put("positionType", progress.getCurrentPositionType());
                result.put("positionValue", progress.getCurrentPositionValue());
            } else {
                result.put("success", false);
                result.put("message", "No position data available");
            }
        }
        return result;
    }

    public List<Checkpoint> getCheckpointHistory(Long id, int limit) {
        LambdaQueryWrapper<Checkpoint> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Checkpoint::getTaskId, id)
                .orderByDesc(Checkpoint::getUpdatedAt)
                .last("LIMIT " + limit);
        return checkpointRepository.selectList(wrapper);
    }

    private Checkpoint getLastCheckpointEntity(Long taskId) {
        LambdaQueryWrapper<Checkpoint> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Checkpoint::getTaskId, taskId)
                .orderByDesc(Checkpoint::getUpdatedAt)
                .last("LIMIT 1");
        return checkpointRepository.selectOne(wrapper);
    }

    public List<TaskLog> getLogs(Long id, int limit) {
        LambdaQueryWrapper<TaskLog> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(TaskLog::getTaskId, id)
                .orderByDesc(TaskLog::getCreatedAt)
                .last("LIMIT " + limit);
        return taskLogRepository.selectList(wrapper);
    }

    public Map<String, Object> getDashboardStats() {
        Map<String, Object> stats = new HashMap<>();
        Long total = taskRepository.selectCount(null);
        stats.put("total", total);

        LambdaQueryWrapper<Task> runningWrapper = new LambdaQueryWrapper<>();
        runningWrapper.eq(Task::getStatus, "running");
        stats.put("running", taskRepository.selectCount(runningWrapper));

        LambdaQueryWrapper<Task> completedWrapper = new LambdaQueryWrapper<>();
        completedWrapper.eq(Task::getStatus, "completed");
        stats.put("completed", taskRepository.selectCount(completedWrapper));

        LambdaQueryWrapper<Task> failedWrapper = new LambdaQueryWrapper<>();
        failedWrapper.eq(Task::getStatus, "failed");
        stats.put("failed", taskRepository.selectCount(failedWrapper));

        LambdaQueryWrapper<Task> rollbackWrapper = new LambdaQueryWrapper<>();
        rollbackWrapper.eq(Task::getStatus, "rollback_completed");
        stats.put("rollbackCompleted", taskRepository.selectCount(rollbackWrapper));

        return stats;
    }
}
