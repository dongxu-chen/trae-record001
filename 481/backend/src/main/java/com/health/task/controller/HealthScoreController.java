package com.health.task.controller;

import com.health.task.dto.AutoRepairResponse;
import com.health.task.dto.DashboardResponse;
import com.health.task.dto.HealthScoreResponse;
import com.health.task.dto.PredictionResponse;
import com.health.task.dto.ScoreTrendPoint;
import com.health.task.dto.SlaPredictionResponse;
import com.health.task.dto.TaskDependencyRequest;
import com.health.task.dto.WeightConfigRequest;
import com.health.task.entity.AutoRepairLog;
import com.health.task.entity.HealthScore;
import com.health.task.entity.HealthScorePrediction;
import com.health.task.entity.SlaPrediction;
import com.health.task.entity.TaskDependency;
import com.health.task.entity.TaskWeightConfig;
import com.health.task.model.HealthScoreResult;
import com.health.task.model.TaskMetrics;
import com.health.task.repository.TaskExecutionRecordRepository;
import com.health.task.service.AutoRepairService;
import com.health.task.service.HealthScorePredictionService;
import com.health.task.service.HealthScoringService;
import com.health.task.service.SlaPredictionService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/health")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class HealthScoreController {

    private final HealthScoringService scoringService;
    private final HealthScorePredictionService predictionService;
    private final AutoRepairService autoRepairService;
    private final SlaPredictionService slaPredictionService;
    private final TaskExecutionRecordRepository executionRepo;
    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @GetMapping("/dashboard")
    public ResponseEntity<DashboardResponse> getDashboard() {
        List<HealthScore> latestScores = scoringService.getLatestScores();

        List<HealthScoreResponse> responses = latestScores.stream()
                .map(this::toResponse)
                .collect(Collectors.toList());

        int healthy = 0, warning = 0, critical = 0;
        double totalScore = 0;
        for (HealthScore hs : latestScores) {
            totalScore += hs.getOverallScore();
            if (hs.getOverallScore() >= 80) healthy++;
            else if (hs.getOverallScore() >= 60) warning++;
            else critical++;
        }

        double avg = latestScores.isEmpty() ? 0 : totalScore / latestScores.size();

        DashboardResponse dashboard = DashboardResponse.builder()
                .totalTasks(latestScores.size())
                .avgScore(Math.round(avg * 10.0) / 10.0)
                .healthyCount(healthy)
                .warningCount(warning)
                .criticalCount(critical)
                .taskScores(responses)
                .build();

        return ResponseEntity.ok(dashboard);
    }

    @GetMapping("/scores")
    public ResponseEntity<List<HealthScoreResponse>> getAllLatestScores() {
        List<HealthScore> scores = scoringService.getLatestScores();
        List<HealthScoreResponse> responses = scores.stream()
                .map(this::toResponse)
                .collect(Collectors.toList());
        return ResponseEntity.ok(responses);
    }

    @GetMapping("/scores/{taskName}")
    public ResponseEntity<HealthScoreResponse> getScoreForTask(@PathVariable String taskName) {
        Optional<HealthScore> scoreOpt = scoringService.getLatestScores().stream()
                .filter(s -> s.getTaskName().equals(taskName))
                .findFirst();

        if (scoreOpt.isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        HealthScoreResponse response = toResponse(scoreOpt.get());

        List<HealthScoreResponse.UpstreamIssue> upstreamIssues = scoringService.checkUpstreamIssues(taskName);
        response.setUpstreamIssues(upstreamIssues);

        TaskWeightConfig weightConfig = scoringService.getWeightConfig(taskName);
        if (weightConfig != null) {
            response.setImportanceLevel(weightConfig.getImportanceLevel());
            List<HealthScoreResponse.DimensionDetail> dimensions = response.getDimensions();
            if (dimensions != null) {
                for (HealthScoreResponse.DimensionDetail d : dimensions) {
                    switch (d.getName()) {
                        case "duration" -> d.setWeight(weightConfig.getDurationWeight());
                        case "success_rate" -> d.setWeight(weightConfig.getSuccessRateWeight());
                        case "frequency" -> d.setWeight(weightConfig.getFrequencyWeight());
                        case "resource" -> d.setWeight(weightConfig.getResourceWeight());
                    }
                }
            }
        }

        LocalDateTime start = LocalDateTime.now().minusHours(24);
        LocalDateTime end = LocalDateTime.now();
        long totalExecutions = executionRepo.countByTaskNameAndTimeRange(taskName, start, end);
        long successExecutions = executionRepo.countSuccessByTaskNameAndTimeRange(taskName, start, end);
        Double avgDuration = executionRepo.avgDurationByTaskNameAndTimeRange(taskName, start, end);
        Double avgCpu = executionRepo.avgCpuByTaskNameAndTimeRange(taskName, start, end);
        Double avgMemory = executionRepo.avgMemoryByTaskNameAndTimeRange(taskName, start, end);
        Long maxDuration = executionRepo.maxDurationByTaskNameAndTimeRange(taskName, start, end);

        TaskMetrics metrics = TaskMetrics.builder()
                .taskName(taskName)
                .avgDurationMs(avgDuration != null ? avgDuration : 0.0)
                .maxDurationMs(maxDuration != null ? maxDuration : 0L)
                .successRate(totalExecutions > 0 ? (double) successExecutions / totalExecutions * 100.0 : 0.0)
                .executionCount((int) totalExecutions)
                .avgCpuUsage(avgCpu != null ? avgCpu : 0.0)
                .avgMemoryUsage(avgMemory != null ? avgMemory : 0.0)
                .build();

        List<HealthScoreResponse.ActionableItem> actionableItems =
                scoringService.generateActionableItems(metrics, scoreOpt.get().getOverallScore());
        response.setActionableItems(actionableItems);

        return ResponseEntity.ok(response);
    }

    @GetMapping("/trend/{taskName}")
    public ResponseEntity<List<ScoreTrendPoint>> getScoreTrend(
            @PathVariable String taskName,
            @RequestParam(defaultValue = "24") int hours) {
        List<HealthScore> trend = scoringService.getScoreTrend(taskName, hours);
        List<ScoreTrendPoint> points = trend.stream()
                .map(this::toTrendPoint)
                .collect(Collectors.toList());
        return ResponseEntity.ok(points);
    }

    @GetMapping("/unhealthy")
    public ResponseEntity<List<HealthScoreResponse>> getUnhealthyTasks(
            @RequestParam(defaultValue = "60") int threshold) {
        List<HealthScore> unhealthy = scoringService.getUnhealthyTasks(threshold);
        List<HealthScoreResponse> responses = unhealthy.stream()
                .map(this::toResponse)
                .collect(Collectors.toList());
        return ResponseEntity.ok(responses);
    }

    @PostMapping("/calculate")
    public ResponseEntity<String> triggerCalculation() {
        scoringService.calculateAndSaveAllScores();
        return ResponseEntity.ok("Health score calculation triggered successfully");
    }

    @GetMapping("/diagnosis/{taskName}")
    public ResponseEntity<HealthScoreResponse> getDiagnosis(@PathVariable String taskName) {
        return getScoreForTask(taskName);
    }

    @GetMapping("/weights/{taskName}")
    public ResponseEntity<TaskWeightConfig> getWeightConfig(@PathVariable String taskName) {
        TaskWeightConfig config = scoringService.getWeightConfig(taskName);
        if (config == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(config);
    }

    @PutMapping("/weights/{taskName}")
    public ResponseEntity<TaskWeightConfig> saveWeightConfig(
            @PathVariable String taskName,
            @RequestBody WeightConfigRequest request) {
        try {
            TaskWeightConfig config = scoringService.saveWeightConfig(
                    taskName,
                    request.getTaskGroup(),
                    request.getImportanceLevel(),
                    request.getDurationWeight(),
                    request.getSuccessRateWeight(),
                    request.getFrequencyWeight(),
                    request.getResourceWeight(),
                    request.getDescription()
            );
            return ResponseEntity.ok(config);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @GetMapping("/weights/default/{importance}")
    public ResponseEntity<TaskWeightConfig> getDefaultWeights(@PathVariable String importance) {
        return ResponseEntity.ok(scoringService.getDefaultWeightsByImportance(importance));
    }

    @GetMapping("/dependencies/{taskName}")
    public ResponseEntity<List<TaskDependency>> getDependencies(@PathVariable String taskName) {
        List<TaskDependency> dependencies = scoringService.getDependencies(taskName);
        return ResponseEntity.ok(dependencies);
    }

    @PostMapping("/dependencies/{taskName}")
    public ResponseEntity<TaskDependency> addDependency(
            @PathVariable String taskName,
            @RequestBody TaskDependencyRequest request) {
        TaskDependency dep = scoringService.saveDependency(
                taskName,
                request.getUpstreamTaskName(),
                request.getDependencyType(),
                request.getMaxWaitSeconds(),
                request.getDescription()
        );
        return ResponseEntity.ok(dep);
    }

    @GetMapping("/upstream-issues/{taskName}")
    public ResponseEntity<List<HealthScoreResponse.UpstreamIssue>> getUpstreamIssues(@PathVariable String taskName) {
        List<HealthScoreResponse.UpstreamIssue> issues = scoringService.checkUpstreamIssues(taskName);
        return ResponseEntity.ok(issues);
    }

    @GetMapping("/predict/{taskName}")
    public ResponseEntity<PredictionResponse> predictHealthScore(
            @PathVariable String taskName,
            @RequestParam(required = false) String taskGroup,
            @RequestParam(required = false) Integer horizonHours) {
        PredictionResponse prediction = predictionService.predictHealthScore(
                taskName,
                taskGroup != null ? taskGroup : "DEFAULT",
                horizonHours);
        return ResponseEntity.ok(prediction);
    }

    @GetMapping("/predict/history/{taskName}")
    public ResponseEntity<List<HealthScorePrediction>> getPredictionHistory(
            @PathVariable String taskName,
            @RequestParam(required = false) String since) {
        LocalDateTime sinceTime = since != null ? LocalDateTime.parse(since) : null;
        List<HealthScorePrediction> history = predictionService.getPredictionHistory(taskName, sinceTime);
        return ResponseEntity.ok(history);
    }

    @PostMapping("/predict/all")
    public ResponseEntity<String> runAllPredictions() {
        List<String> taskNames = List.of("DataSyncJob", "ReportGenerateJob", "CacheCleanJob",
                "EmailNotifyJob", "LogArchiveJob", "BackupJob", "IndexRebuildJob");
        for (String taskName : taskNames) {
            predictionService.predictHealthScore(taskName, "DEFAULT", 72);
        }
        return ResponseEntity.ok("Health score predictions triggered for all tasks");
    }

    @GetMapping("/auto-repair/{taskName}")
    public ResponseEntity<AutoRepairResponse> analyzeAndRepair(
            @PathVariable String taskName,
            @RequestParam(required = false) String taskGroup) {
        AutoRepairResponse response = autoRepairService.analyzeAndRepair(
                taskName,
                taskGroup != null ? taskGroup : "DEFAULT");
        return ResponseEntity.ok(response);
    }

    @GetMapping("/auto-repair/history/{taskName}")
    public ResponseEntity<List<AutoRepairLog>> getRepairHistory(
            @PathVariable String taskName,
            @RequestParam(required = false) String since) {
        LocalDateTime sinceTime = since != null ? LocalDateTime.parse(since) : null;
        List<AutoRepairLog> history = autoRepairService.getRepairHistory(taskName, sinceTime);
        return ResponseEntity.ok(history);
    }

    @PostMapping("/auto-repair/manual/{taskName}")
    public ResponseEntity<AutoRepairLog> applyManualRepair(
            @PathVariable String taskName,
            @RequestBody Map<String, String> request) {
        AutoRepairLog repair = autoRepairService.applyManualRepair(
                taskName,
                request.getOrDefault("taskGroup", "DEFAULT"),
                request.get("repairAction"),
                request.get("oldValue"),
                request.get("newValue"),
                request.get("riskLevel"));
        return ResponseEntity.ok(repair);
    }

    @PutMapping("/auto-repair/status/{repairId}")
    public ResponseEntity<String> updateRepairStatus(
            @PathVariable Long repairId,
            @RequestBody Map<String, Object> request) {
        String status = (String) request.get("status");
        Double successRateAfter = request.get("successRateAfter") != null
                ? ((Number) request.get("successRateAfter")).doubleValue() : null;
        Integer followUpScore = request.get("followUpScore") != null
                ? ((Number) request.get("followUpScore")).intValue() : null;
        String result = autoRepairService.updateRepairStatus(repairId, status, successRateAfter, followUpScore);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/auto-repair/all")
    public ResponseEntity<String> runAutoRepairForAll() {
        autoRepairService.runAutoRepairForAllTasks();
        return ResponseEntity.ok("Auto-repair analysis triggered for all tasks");
    }

    @GetMapping("/sla/{taskName}")
    public ResponseEntity<SlaPredictionResponse> predictSla(
            @PathVariable String taskName,
            @RequestParam(required = false) String taskGroup,
            @RequestParam(required = false) Integer slaTarget) {
        SlaPredictionResponse response = slaPredictionService.predictSlaAchievement(
                taskName,
                taskGroup != null ? taskGroup : "DEFAULT",
                slaTarget);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/sla/history/{taskName}")
    public ResponseEntity<List<SlaPrediction>> getSlaHistory(
            @PathVariable String taskName,
            @RequestParam(required = false) String since) {
        LocalDateTime sinceTime = since != null ? LocalDateTime.parse(since) : null;
        List<SlaPrediction> history = slaPredictionService.getSlaPredictionHistory(taskName, sinceTime);
        return ResponseEntity.ok(history);
    }

    @PostMapping("/sla/all")
    public ResponseEntity<String> runSlaPredictionForAll() {
        slaPredictionService.runSlaPredictionForAllTasks();
        return ResponseEntity.ok("SLA prediction triggered for all tasks");
    }

    private HealthScoreResponse toResponse(HealthScore hs) {
        TaskWeightConfig weightConfig = scoringService.getWeightConfig(hs.getTaskName());
        double durationWeight = weightConfig != null ? weightConfig.getDurationWeight() : 0.25;
        double successRateWeight = weightConfig != null ? weightConfig.getSuccessRateWeight() : 0.35;
        double frequencyWeight = weightConfig != null ? weightConfig.getFrequencyWeight() : 0.15;
        double resourceWeight = weightConfig != null ? weightConfig.getResourceWeight() : 0.25;

        return HealthScoreResponse.builder()
                .taskName(hs.getTaskName())
                .taskGroup(hs.getTaskGroup())
                .overallScore(hs.getOverallScore())
                .scoreLevel(getScoreLevel(hs.getOverallScore()))
                .importanceLevel(weightConfig != null ? weightConfig.getImportanceLevel() : "MEDIUM")
                .dimensions(List.of(
                        HealthScoreResponse.DimensionDetail.builder()
                                .name("duration").score(hs.getDurationScore())
                                .weight(durationWeight).build(),
                        HealthScoreResponse.DimensionDetail.builder()
                                .name("success_rate").score(hs.getSuccessRateScore())
                                .weight(successRateWeight).build(),
                        HealthScoreResponse.DimensionDetail.builder()
                                .name("frequency").score(hs.getFrequencyScore())
                                .weight(frequencyWeight).build(),
                        HealthScoreResponse.DimensionDetail.builder()
                                .name("resource").score(hs.getResourceScore())
                                .weight(resourceWeight).build()
                ))
                .diagnosis(hs.getDiagnosis())
                .suggestion(hs.getSuggestion())
                .calculatedAt(hs.getCalculatedAt().format(FMT))
                .build();
    }

    private ScoreTrendPoint toTrendPoint(HealthScore hs) {
        return ScoreTrendPoint.builder()
                .timestamp(hs.getCalculatedAt().format(FMT))
                .overallScore(hs.getOverallScore())
                .durationScore(hs.getDurationScore())
                .successRateScore(hs.getSuccessRateScore())
                .frequencyScore(hs.getFrequencyScore())
                .resourceScore(hs.getResourceScore())
                .build();
    }

    private String getScoreLevel(int score) {
        if (score >= 90) return "HEALTHY";
        if (score >= 80) return "GOOD";
        if (score >= 60) return "WARNING";
        if (score >= 40) return "POOR";
        return "CRITICAL";
    }
}
