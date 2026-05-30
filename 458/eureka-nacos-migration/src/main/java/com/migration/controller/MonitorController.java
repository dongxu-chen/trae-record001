package com.migration.controller;

import com.migration.monitor.MigrationMonitor;
import com.migration.model.ConsistencyCheckResult;
import com.migration.model.MigrationProgress;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/monitor")
public class MonitorController {

    private final MigrationMonitor monitor;

    public MonitorController(MigrationMonitor monitor) {
        this.monitor = monitor;
    }

    @GetMapping("/dashboard")
    public ResponseEntity<Map<String, Object>> getDashboard() {
        return ResponseEntity.ok(monitor.getDashboardData());
    }

    @GetMapping("/progress/{taskId}")
    public ResponseEntity<MigrationProgress> getProgress(@PathVariable String taskId) {
        MigrationProgress progress = monitor.getProgress(taskId);
        if (progress == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(progress);
    }

    @GetMapping("/progress")
    public ResponseEntity<List<MigrationProgress>> getAllProgress() {
        return ResponseEntity.ok(monitor.getAllProgress());
    }

    @GetMapping("/consistency/history")
    public ResponseEntity<List<ConsistencyCheckResult>> getConsistencyHistory() {
        return ResponseEntity.ok(monitor.getCheckHistory());
    }

    @GetMapping("/consistency/latest")
    public ResponseEntity<Object> getLatestConsistencyCheck() {
        List<ConsistencyCheckResult> history = monitor.getCheckHistory();
        if (history.isEmpty()) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("message", "No consistency checks performed yet");
            return ResponseEntity.ok(empty);
        }
        return ResponseEntity.ok(history.get(history.size() - 1));
    }

    @GetMapping("/tasks")
    public ResponseEntity<Object> getTasks() {
        return ResponseEntity.ok(monitor.getAllTasks());
    }

    @GetMapping("/task/{taskId}")
    public ResponseEntity<Object> getTask(@PathVariable String taskId) {
        Object task = monitor.getTask(taskId);
        if (task == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(task);
    }
}
