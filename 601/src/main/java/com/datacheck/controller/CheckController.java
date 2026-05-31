package com.datacheck.controller;

import com.datacheck.check.CheckEngine;
import com.datacheck.datasource.DataSourceAdapter;
import com.datacheck.datasource.DataSourceAdapterFactory;
import com.datacheck.model.*;
import com.datacheck.model.enums.DataSourceType;
import com.datacheck.repair.AutoRepairService;
import com.datacheck.service.GrayReleaseService;
import com.datacheck.service.PredictiveCheckService;
import com.datacheck.service.ReportService;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@RestController
@RequestMapping("/check")
@CrossOrigin(origins = "*")
public class CheckController {

    private final CheckEngine checkEngine;
    private final DataSourceAdapterFactory adapterFactory;
    private final AutoRepairService autoRepairService;
    private final ReportService reportService;
    private final GrayReleaseService grayReleaseService;
    private final PredictiveCheckService predictiveCheckService;
    private final Map<String, CheckTask> taskStore = new LinkedHashMap<>();

    @Autowired
    public CheckController(CheckEngine checkEngine,
                           DataSourceAdapterFactory adapterFactory,
                           AutoRepairService autoRepairService,
                           ReportService reportService,
                           GrayReleaseService grayReleaseService,
                           PredictiveCheckService predictiveCheckService) {
        this.checkEngine = checkEngine;
        this.adapterFactory = adapterFactory;
        this.autoRepairService = autoRepairService;
        this.reportService = reportService;
        this.grayReleaseService = grayReleaseService;
        this.predictiveCheckService = predictiveCheckService;
    }

    @PostMapping("/task")
    public ResponseEntity<Map<String, Object>> createTask(@Valid @RequestBody CheckTask task) {
        task.setId(UUID.randomUUID().toString());
        task.setCreatedAt(LocalDateTime.now());
        task.setStatus("PENDING");
        taskStore.put(task.getId(), task);

        log.info("Created check task: {}, type: {}, table: {}",
                task.getId(), task.getSourceType(), task.getTableName());

        return ResponseEntity.ok(Map.of(
                "success", true,
                "taskId", task.getId(),
                "message", "Task created successfully"
        ));
    }

    @PostMapping("/task/{taskId}/start")
    public ResponseEntity<Map<String, Object>> startTask(@PathVariable String taskId) {
        CheckTask task = taskStore.get(taskId);
        if (task == null) {
            return ResponseEntity.notFound().build();
        }
        if ("RUNNING".equals(task.getStatus())) {
            return ResponseEntity.badRequest().body(Map.of(
                    "success", false,
                    "message", "Task is already running"
            ));
        }

        checkEngine.executeCheck(task);
        log.info("Started check task: {}", taskId);

        return ResponseEntity.ok(Map.of(
                "success", true,
                "taskId", taskId,
                "message", "Task started successfully"
        ));
    }

    @PostMapping("/task/execute")
    public ResponseEntity<Map<String, Object>> executeTask(@Valid @RequestBody CheckTask task) {
        task.setId(UUID.randomUUID().toString());
        task.setCreatedAt(LocalDateTime.now());
        task.setStatus("PENDING");
        taskStore.put(task.getId(), task);

        checkEngine.executeCheck(task);
        log.info("Created and started check task: {}, type: {}, table: {}",
                task.getId(), task.getSourceType(), task.getTableName());

        return ResponseEntity.ok(Map.of(
                "success", true,
                "taskId", task.getId(),
                "message", "Task created and started successfully"
        ));
    }

    @PostMapping("/task/{taskId}/cancel")
    public ResponseEntity<Map<String, Object>> cancelTask(@PathVariable String taskId) {
        boolean cancelled = checkEngine.cancelTask(taskId);
        if (cancelled) {
            CheckTask task = taskStore.get(taskId);
            if (task != null) {
                task.setStatus("CANCELLED");
                task.setFinishedAt(LocalDateTime.now());
            }
            return ResponseEntity.ok(Map.of(
                    "success", true,
                    "message", "Task cancelled successfully"
            ));
        }
        return ResponseEntity.badRequest().body(Map.of(
                "success", false,
                "message", "Task not found or not running"
        ));
    }

    @GetMapping("/task/{taskId}")
    public ResponseEntity<CheckTask> getTask(@PathVariable String taskId) {
        CheckTask task = taskStore.get(taskId);
        if (task == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(task);
    }

    @GetMapping("/tasks")
    public ResponseEntity<List<CheckTask>> getTasks(
            @RequestParam(required = false) DataSourceType sourceType,
            @RequestParam(required = false) String status) {
        List<CheckTask> tasks = new ArrayList<>(taskStore.values());
        if (sourceType != null) {
            tasks = tasks.stream()
                    .filter(t -> t.getSourceType() == sourceType)
                    .collect(Collectors.toList());
        }
        if (status != null) {
            tasks = tasks.stream()
                    .filter(t -> status.equals(t.getStatus()))
                    .collect(Collectors.toList());
        }
        tasks.sort((a, b) -> b.getCreatedAt().compareTo(a.getCreatedAt()));
        return ResponseEntity.ok(tasks);
    }

    @GetMapping("/task/{taskId}/result")
    public ResponseEntity<CheckResult> getResult(@PathVariable String taskId) {
        return checkEngine.getResult(taskId)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/results")
    public ResponseEntity<Collection<CheckResult>> getRecentResults() {
        return ResponseEntity.ok(checkEngine.getRecentResults());
    }

    @GetMapping("/running")
    public ResponseEntity<Collection<CheckTask>> getRunningTasks() {
        return ResponseEntity.ok(checkEngine.getRunningTasks());
    }

    @PostMapping("/repair/{diffId}")
    public ResponseEntity<Map<String, Object>> triggerRepair(
            @PathVariable String diffId,
            @RequestParam String taskId) {
        CheckTask task = taskStore.get(taskId);
        if (task == null) {
            return ResponseEntity.notFound().build();
        }

        Optional<CheckResult> resultOpt = checkEngine.getResult(taskId);
        if (resultOpt.isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of(
                    "success", false,
                    "message", "Check result not found"
            ));
        }

        Optional<DiffResult> diffOpt = resultOpt.get().getDiffs().stream()
                .filter(d -> diffId.equals(d.getId()))
                .findFirst();

        if (diffOpt.isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of(
                    "success", false,
                    "message", "Diff not found"
            ));
        }

        autoRepairService.repair(diffOpt.get(), task);

        return ResponseEntity.ok(Map.of(
                "success", true,
                "message", "Repair triggered successfully"
        ));
    }

    @GetMapping("/datasources")
    public ResponseEntity<List<Map<String, Object>>> getDataSources() {
        List<Map<String, Object>> dataSources = new ArrayList<>();
        for (DataSourceType type : DataSourceType.values()) {
            Map<String, Object> ds = new LinkedHashMap<>();
            ds.put("type", type.name());
            ds.put("name", type.name().charAt(0) + type.name().substring(1).toLowerCase());

            try {
                DataSourceAdapter adapter = adapterFactory.getAdapter(type);
                ds.put("available", true);
            } catch (Exception e) {
                ds.put("available", false);
            }
            dataSources.add(ds);
        }
        return ResponseEntity.ok(dataSources);
    }

    @GetMapping("/datasource/{type}/tables")
    public ResponseEntity<List<String>> getTables(@PathVariable DataSourceType type) {
        try {
            DataSourceAdapter adapter = adapterFactory.getAdapter(type);
            return ResponseEntity.ok(Collections.emptyList());
        } catch (Exception e) {
            log.error("Failed to get tables for type: {}", type, e);
            return ResponseEntity.ok(Collections.emptyList());
        }
    }

    @GetMapping("/datasource/{type}/table/{tableName}/columns")
    public ResponseEntity<List<String>> getColumns(
            @PathVariable DataSourceType type,
            @PathVariable String tableName) {
        try {
            DataSourceAdapter adapter = adapterFactory.getAdapter(type);
            return ResponseEntity.ok(adapter.getColumns(tableName));
        } catch (Exception e) {
            log.error("Failed to get columns for type: {}, table: {}", type, tableName, e);
            return ResponseEntity.ok(Collections.emptyList());
        }
    }

    @GetMapping("/diffs")
    public ResponseEntity<List<DiffResult>> getDiffs(
            @RequestParam(required = false) String diffType,
            @RequestParam(required = false) String repairStatus,
            @RequestParam(required = false) String tableName) {
        List<DiffResult> diffs = new ArrayList<>(checkEngine.getAllDiffs());

        if (diffType != null) {
            diffs = diffs.stream()
                    .filter(d -> diffType.equals(d.getDiffType().name()))
                    .collect(Collectors.toList());
        }
        if (repairStatus != null) {
            diffs = diffs.stream()
                    .filter(d -> repairStatus.equals(d.getRepairStatus().name()))
                    .collect(Collectors.toList());
        }
        if (tableName != null) {
            diffs = diffs.stream()
                    .filter(d -> tableName.equals(d.getTableName()))
                    .collect(Collectors.toList());
        }

        diffs.sort((a, b) -> b.getDetectedAt().compareTo(a.getDetectedAt()));
        return ResponseEntity.ok(diffs);
    }

    @GetMapping("/diff/{diffId}")
    public ResponseEntity<DiffResult> getDiff(@PathVariable String diffId) {
        return checkEngine.getDiff(diffId)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/statistics")
    public ResponseEntity<Map<String, Object>> getStatistics() {
        Map<String, Object> stats = new LinkedHashMap<>();

        long totalTasks = taskStore.size();
        long completedTasks = taskStore.values().stream()
                .filter(t -> "COMPLETED".equals(t.getStatus()))
                .count();
        long runningTasks = checkEngine.getRunningTasks().size();
        long failedTasks = taskStore.values().stream()
                .filter(t -> "FAILED".equals(t.getStatus()))
                .count();

        Collection<DiffResult> allDiffs = checkEngine.getAllDiffs();
        long totalDiffs = allDiffs.size();
        long totalRepaired = allDiffs.stream()
                .filter(d -> d.getRepairStatus() != null &&
                        "SUCCESS".equals(d.getRepairStatus().name()))
                .count();
        long pendingRepair = allDiffs.stream()
                .filter(d -> d.getRepairStatus() != null &&
                        "PENDING".equals(d.getRepairStatus().name()))
                .count();

        stats.put("totalTasks", totalTasks);
        stats.put("completedTasks", completedTasks);
        stats.put("runningTasks", runningTasks);
        stats.put("failedTasks", failedTasks);
        stats.put("totalDiffs", totalDiffs);
        stats.put("totalRepaired", totalRepaired);
        stats.put("pendingRepair", pendingRepair);
        stats.put("repairRate", totalDiffs > 0 ? (double) totalRepaired / totalDiffs : 0);

        return ResponseEntity.ok(stats);
    }

    @PostMapping("/report/{taskId}")
    public ResponseEntity<CheckReport> generateReport(@PathVariable String taskId) {
        CheckReport report = reportService.generateReport(taskId);
        if (report == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(report);
    }

    @GetMapping("/report/latest")
    public ResponseEntity<CheckReport> getLatestReport() {
        CheckReport report = reportService.generateLatestReport();
        if (report == null) {
            return ResponseEntity.noContent().build();
        }
        return ResponseEntity.ok(report);
    }

    @GetMapping("/reports")
    public ResponseEntity<Collection<CheckReport>> getAllReports() {
        return ResponseEntity.ok(reportService.getAllReports());
    }

    @GetMapping("/report/{reportId}")
    public ResponseEntity<CheckReport> getReport(@PathVariable String reportId) {
        return reportService.getReport(reportId)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/gray")
    public ResponseEntity<GrayReleaseConfig> createGrayConfig(@RequestBody GrayReleaseConfig config) {
        return ResponseEntity.ok(grayReleaseService.createGrayConfig(config));
    }

    @GetMapping("/gray")
    public ResponseEntity<Collection<GrayReleaseConfig>> getAllGrayConfigs() {
        return ResponseEntity.ok(grayReleaseService.getAllGrayConfigs());
    }

    @GetMapping("/gray/{configId}")
    public ResponseEntity<GrayReleaseConfig> getGrayConfig(@PathVariable String configId) {
        GrayReleaseConfig config = grayReleaseService.getGrayConfig(configId);
        if (config == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(config);
    }

    @PostMapping("/gray/{configId}/execute")
    public ResponseEntity<Map<String, Object>> executeGrayCheck(
            @PathVariable String configId,
            @RequestBody CheckTask baseTask) {
        grayReleaseService.executeGrayCheck(configId, baseTask);
        return ResponseEntity.ok(Map.of(
                "success", true,
                "message", "Gray release check started"
        ));
    }

    @PostMapping("/gray/{configId}/advance")
    public ResponseEntity<GrayReleaseConfig> advanceGrayPhase(@PathVariable String configId) {
        GrayReleaseConfig config = grayReleaseService.advancePhase(configId);
        if (config == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(config);
    }

    @PostMapping("/gray/{configId}/pause")
    public ResponseEntity<GrayReleaseConfig> pauseGrayRelease(@PathVariable String configId) {
        GrayReleaseConfig config = grayReleaseService.pauseGrayRelease(configId);
        if (config == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(config);
    }

    @PostMapping("/gray/{configId}/resume")
    public ResponseEntity<GrayReleaseConfig> resumeGrayRelease(@PathVariable String configId) {
        GrayReleaseConfig config = grayReleaseService.resumeGrayRelease(configId);
        if (config == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(config);
    }

    @GetMapping("/predictions")
    public ResponseEntity<Collection<PredictiveCheckService.PredictionResult>> getAllPredictions() {
        return ResponseEntity.ok(predictiveCheckService.getAllPredictions());
    }

    @GetMapping("/prediction/{tableName}")
    public ResponseEntity<PredictiveCheckService.PredictionResult> getPrediction(
            @PathVariable String tableName) {
        PredictiveCheckService.PredictionResult prediction = predictiveCheckService.getPrediction(tableName);
        if (prediction == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(prediction);
    }

    @GetMapping("/prediction/{tableName}/trend")
    public ResponseEntity<List<PredictiveCheckService.TrendDataPoint>> getTrendData(
            @PathVariable String tableName) {
        return ResponseEntity.ok(predictiveCheckService.getTrendData(tableName));
    }
}
