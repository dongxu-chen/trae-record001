package com.migration.monitor;

import com.migration.model.ConsistencyCheckResult;
import com.migration.model.MigrationProgress;
import com.migration.model.MigrationTask;
import com.migration.model.ServiceInstance;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class MigrationMonitor {

    private final Map<String, MigrationTask> tasks = new ConcurrentHashMap<>();
    private final Map<String, Map<String, List<ServiceInstance>>> snapshots = new ConcurrentHashMap<>();
    private final List<ConsistencyCheckResult> checkHistory = Collections.synchronizedList(new ArrayList<>());

    public void registerTask(MigrationTask task) {
        tasks.put(task.getTaskId(), task);
        log.info("Registered migration task: {}", task.getTaskId());
    }

    public void updateProgress(String taskId, MigrationTask.TaskPhase phase, int progress) {
        MigrationTask task = tasks.get(taskId);
        if (task != null) {
            task.setPhase(phase);
            task.setProgress(progress);
            log.info("Task {} progress: phase={}, progress={}%", taskId, phase, progress);
        }
    }

    public void updateSnapshot(String taskId, Map<String, List<ServiceInstance>> snapshot) {
        snapshots.put(taskId, snapshot);
    }

    public void recordConsistencyCheck(String taskId, ConsistencyCheckResult result) {
        checkHistory.add(result);
        log.info("Recorded consistency check for task {}: {}", taskId, result.isConsistent() ? "PASSED" : "FAILED");
    }

    public MigrationProgress getProgress(String taskId) {
        MigrationTask task = tasks.get(taskId);
        if (task == null) return null;

        Map<String, List<ServiceInstance>> snapshot = snapshots.get(taskId);
        int totalServices = snapshot != null ? snapshot.size() : 0;

        long elapsed = System.currentTimeMillis() - task.getStartTime();
        long estimated = task.getProgress() > 0
                ? (elapsed * 100 / task.getProgress()) - elapsed
                : 0;

        return MigrationProgress.builder()
                .taskId(taskId)
                .currentPhase(task.getPhase())
                .currentStatus(task.getStatus())
                .totalServices(totalServices)
                .completedServices((int) (totalServices * task.getProgress() / 100.0))
                .failedServices(0)
                .progressPercent(task.getProgress())
                .currentService(task.getServiceId())
                .elapsedTimeMs(elapsed)
                .estimatedRemainingMs(Math.max(0, estimated))
                .build();
    }

    public List<MigrationProgress> getAllProgress() {
        List<MigrationProgress> progressList = new ArrayList<>();
        for (String taskId : tasks.keySet()) {
            MigrationProgress progress = getProgress(taskId);
            if (progress != null) {
                progressList.add(progress);
            }
        }
        return progressList;
    }

    public List<ConsistencyCheckResult> getCheckHistory() {
        return Collections.unmodifiableList(checkHistory);
    }

    public MigrationTask getTask(String taskId) {
        return tasks.get(taskId);
    }

    public Collection<MigrationTask> getAllTasks() {
        return tasks.values();
    }

    public Map<String, Object> getDashboardData() {
        Map<String, Object> dashboard = new LinkedHashMap<>();

        dashboard.put("totalTasks", tasks.size());
        dashboard.put("runningTasks", tasks.values().stream()
                .filter(t -> t.getStatus() == MigrationTask.TaskStatus.RUNNING).count());
        dashboard.put("completedTasks", tasks.values().stream()
                .filter(t -> t.getStatus() == MigrationTask.TaskStatus.SUCCESS).count());
        dashboard.put("failedTasks", tasks.values().stream()
                .filter(t -> t.getStatus() == MigrationTask.TaskStatus.FAILED).count());
        dashboard.put("rollbackTasks", tasks.values().stream()
                .filter(t -> t.getStatus() == MigrationTask.TaskStatus.ROLLBACK).count());

        dashboard.put("totalConsistencyChecks", checkHistory.size());
        dashboard.put("passedChecks", checkHistory.stream().filter(ConsistencyCheckResult::isConsistent).count());
        dashboard.put("failedChecks", checkHistory.stream().filter(r -> !r.isConsistent()).count());

        if (!checkHistory.isEmpty()) {
            ConsistencyCheckResult latest = checkHistory.get(checkHistory.size() - 1);
            dashboard.put("latestCheck", latest);
        }

        return dashboard;
    }
}
