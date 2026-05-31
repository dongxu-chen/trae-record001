package com.depguard.controller;

import com.depguard.dto.*;
import com.depguard.engine.DependencyHealthScorer;
import com.depguard.engine.DependencyUsageAnalyzer;
import com.depguard.entity.DependencyRecord;
import com.depguard.entity.ScanResult;
import com.depguard.entity.UpgradeSuggestionRecord;
import com.depguard.repository.ScanResultRepository;
import com.depguard.service.AutoUpgradeService;
import com.depguard.service.DependencyParserService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class DependencyHealthController {

    private final DependencyHealthScorer healthScorer;
    private final DependencyUsageAnalyzer usageAnalyzer;
    private final AutoUpgradeService autoUpgradeService;
    private final DependencyParserService dependencyParserService;
    private final ScanResultRepository scanResultRepository;

    @GetMapping("/services/{repoId}/health")
    public ResponseEntity<ProjectHealthResponse> getProjectHealth(@PathVariable Long repoId) {
        List<ScanResult> scans = scanResultRepository.findByRepoId(repoId);
        if (scans.isEmpty()) {
            return ResponseEntity.ok(createEmptyHealthResponse());
        }

        ScanResult latestScan = scans.stream()
                .max((a, b) -> a.getScanTime().compareTo(b.getScanTime()))
                .orElse(null);

        List<DependencyRecord> deps = dependencyParserService.getDependenciesByScan(latestScan.getId());

        Map<String, Object> summary = healthScorer.getProjectHealthSummary(deps);

        List<ProjectHealthResponse.DependencyWithHealth> depWithHealth = deps.stream()
                .map(dep -> {
                    DependencyHealthScorer.HealthScore score = healthScorer.calculateHealthScore(dep);
                    DependencyResponse depResponse = toDependencyResponse(dep);
                    return new ProjectHealthResponse.DependencyWithHealth(
                            depResponse,
                            toHealthScoreResponse(score)
                    );
                })
                .sorted((a, b) -> Double.compare(
                        a.getHealthScore().getOverallScore(),
                        b.getHealthScore().getOverallScore()
                ))
                .collect(Collectors.toList());

        ProjectHealthResponse response = new ProjectHealthResponse(
                ((Number) summary.get("overallScore")).doubleValue(),
                (String) summary.get("grade"),
                (Integer) summary.get("healthyCount"),
                (Integer) summary.get("warningCount"),
                (Integer) summary.get("criticalCount"),
                ((Number) summary.get("averageVulnerabilityScore")).doubleValue(),
                ((Number) summary.get("averageFreshnessScore")).doubleValue(),
                ((Number) summary.get("averagePopularityScore")).doubleValue(),
                depWithHealth
        );

        return ResponseEntity.ok(response);
    }

    @GetMapping("/services/{repoId}/dependencies/{depId}/health")
    public ResponseEntity<HealthScoreResponse> getDependencyHealth(@PathVariable Long repoId,
                                                                   @PathVariable Long depId) {
        List<ScanResult> scans = scanResultRepository.findByRepoId(repoId);
        if (scans.isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        ScanResult latestScan = scans.stream()
                .max((a, b) -> a.getScanTime().compareTo(b.getScanTime()))
                .orElse(null);

        List<DependencyRecord> deps = dependencyParserService.getDependenciesByScan(latestScan.getId());

        DependencyRecord dep = deps.stream()
                .filter(d -> d.getId().equals(depId))
                .findFirst()
                .orElse(null);

        if (dep == null) {
            return ResponseEntity.notFound().build();
        }

        DependencyHealthScorer.HealthScore score = healthScorer.calculateHealthScore(dep);
        return ResponseEntity.ok(toHealthScoreResponse(score));
    }

    @PostMapping("/services/{repoId}/usage-analysis")
    public ResponseEntity<UsageAnalysisResponse> analyzeUsage(@PathVariable Long repoId,
                                                              @RequestBody(required = false) Map<String, String> request) {
        List<ScanResult> scans = scanResultRepository.findByRepoId(repoId);
        if (scans.isEmpty()) {
            return ResponseEntity.ok(createEmptyUsageResponse());
        }

        ScanResult latestScan = scans.stream()
                .max((a, b) -> a.getScanTime().compareTo(b.getScanTime()))
                .orElse(null);

        List<DependencyRecord> deps = dependencyParserService.getDependenciesByScan(latestScan.getId());

        List<DependencyUsageAnalyzer.DependencyInfo> depInfos = deps.stream()
                .map(dep -> new DependencyUsageAnalyzer.DependencyInfo(
                        dep.getGroupId(),
                        dep.getArtifactId(),
                        dep.getVersion(),
                        dep.getScope(),
                        dep.getIsDirect()
                ))
                .collect(Collectors.toList());

        String projectRoot = request != null ? request.getOrDefault("projectRoot", ".") : ".";

        DependencyUsageAnalyzer.UsageAnalysisResult result = usageAnalyzer.analyzeUsage(projectRoot, depInfos);

        List<DependencyUsageResponse> depResponses = result.getDependencyResults().stream()
                .map(this::toUsageResponse)
                .collect(Collectors.toList());

        List<DependencyUsageResponse> unusedResponses = result.getUnusedDependencies().stream()
                .map(this::toUsageResponse)
                .collect(Collectors.toList());

        UsageAnalysisResponse response = new UsageAnalysisResponse(
                depResponses,
                result.getUsedCount(),
                result.getUnusedCount(),
                result.getUnclearCount(),
                unusedResponses,
                result.getAllImportedPackages(),
                result.getAllUsedClasses()
        );

        return ResponseEntity.ok(response);
    }

    @GetMapping("/services/{repoId}/auto-upgrade/candidates")
    public ResponseEntity<AutoUpgradeResponse> getAutoUpgradeCandidates(@PathVariable Long repoId) {
        AutoUpgradeService.AutoUpgradeResult result = autoUpgradeService.getAutoUpgradeCandidates(repoId);

        List<UpgradeResponse> autoCandidates = result.getAutoUpgradeCandidates().stream()
                .map(this::toUpgradeResponse)
                .collect(Collectors.toList());

        List<UpgradeResponse> manualCandidates = result.getManualReviewRequired().stream()
                .map(this::toUpgradeResponse)
                .collect(Collectors.toList());

        AutoUpgradeResponse response = new AutoUpgradeResponse(
                autoCandidates,
                manualCandidates,
                result.getSummary()
        );

        return ResponseEntity.ok(response);
    }

    @PostMapping("/services/{repoId}/auto-upgrade/execute")
    public ResponseEntity<AutoUpgradeResponse.ExecutionResponse> executeAutoUpgrade(
            @PathVariable Long repoId,
            @RequestBody(required = false) Map<String, String> request) {
        String userId = request != null ? request.get("userId") : "system";

        AutoUpgradeService.AutoUpgradeExecutionResult result =
                autoUpgradeService.executeAutoUpgrade(repoId, userId);

        List<AutoUpgradeResponse.UpgradeResult> successes = result.getSuccesses().stream()
                .map(this::toAutoUpgradeResult)
                .collect(Collectors.toList());

        List<AutoUpgradeResponse.UpgradeResult> failures = result.getFailures().stream()
                .map(this::toAutoUpgradeResult)
                .collect(Collectors.toList());

        List<AutoUpgradeResponse.UpgradeResult> skipped = result.getSkipped().stream()
                .map(this::toAutoUpgradeResult)
                .collect(Collectors.toList());

        AutoUpgradeResponse.ExecutionResponse response = new AutoUpgradeResponse.ExecutionResponse(
                result.getStartTime(),
                result.getEndTime(),
                result.getTotalRequested(),
                result.getSuccessCount(),
                result.getFailureCount(),
                result.getSkippedCount(),
                successes,
                failures,
                skipped,
                result.getPrUrl(),
                result.getPrError()
        );

        return ResponseEntity.ok(response);
    }

    @GetMapping("/auto-upgrade/config")
    public ResponseEntity<AutoUpgradeResponse.ConfigResponse> getAutoUpgradeConfig() {
        AutoUpgradeService.AutoUpgradeConfig config = autoUpgradeService.getAutoUpgradeConfig();

        AutoUpgradeResponse.ConfigResponse response = new AutoUpgradeResponse.ConfigResponse(
                config.getMinCompatibilityScore(),
                config.getMinHealthScore(),
                config.getAllowedUpgradeTypes(),
                config.getAllowedRiskLevels()
        );

        return ResponseEntity.ok(response);
    }

    private ProjectHealthResponse createEmptyHealthResponse() {
        return new ProjectHealthResponse(
                0.0, "N/A", 0, 0, 0, 0.0, 0.0, 0.0, List.of()
        );
    }

    private UsageAnalysisResponse createEmptyUsageResponse() {
        return new UsageAnalysisResponse(
                List.of(), 0, 0, 0, List.of(), java.util.Set.of(), java.util.Set.of()
        );
    }

    private DependencyResponse toDependencyResponse(DependencyRecord d) {
        return new DependencyResponse(
                d.getId(), d.getScanId(), d.getGroupId(), d.getArtifactId(),
                d.getVersion(), d.getLatestVersion(), d.getScope(),
                d.getIsDirect(), d.getIsOutdated()
        );
    }

    private HealthScoreResponse toHealthScoreResponse(DependencyHealthScorer.HealthScore s) {
        return new HealthScoreResponse(
                s.getDependencyKey(),
                s.getOverallScore(),
                s.getGrade(),
                s.getVulnerabilityScore(),
                s.getFreshnessScore(),
                s.getPopularityScore(),
                s.getRecommendations()
        );
    }

    private DependencyUsageResponse toUsageResponse(DependencyUsageAnalyzer.DependencyUsageResult r) {
        return new DependencyUsageResponse(
                r.getDependency().getGroupId(),
                r.getDependency().getArtifactId(),
                r.getDependency().getVersion(),
                r.getDependency().getScope(),
                r.isUsed(),
                r.isDirectlyUsed(),
                r.getUsageConfidence(),
                r.getUsageEvidence(),
                r.isSpecialScope()
        );
    }

    private UpgradeResponse toUpgradeResponse(UpgradeSuggestionRecord u) {
        return new UpgradeResponse(
                u.getId(), u.getRepoId(), u.getGroupId(), u.getArtifactId(),
                u.getCurrentVersion(), u.getTargetVersion(), u.getUpgradeType(),
                u.getRiskLevel(), u.getCompatibilityScore(), u.getBreakingChanges()
        );
    }

    private AutoUpgradeResponse.UpgradeResult toAutoUpgradeResult(AutoUpgradeService.UpgradeResult r) {
        return new AutoUpgradeResponse.UpgradeResult(
                r.getGroupId(),
                r.getArtifactId(),
                r.getCurrentVersion(),
                r.getTargetVersion(),
                r.isSuccess(),
                r.isSkipped(),
                r.getMessage()
        );
    }
}
