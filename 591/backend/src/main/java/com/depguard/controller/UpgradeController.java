package com.depguard.controller;

import com.depguard.dto.BatchPRRequest;
import com.depguard.dto.CompatibilityResponse;
import com.depguard.dto.UpgradeResponse;
import com.depguard.entity.Repository;
import com.depguard.entity.UpgradeSuggestionRecord;
import com.depguard.repository.RepositoryRepository;
import com.depguard.service.BuildVerificationService;
import com.depguard.service.GitHubIntegrationService;
import com.depguard.service.UpgradeSuggestionService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/upgrades")
@RequiredArgsConstructor
public class UpgradeController {

    private final UpgradeSuggestionService upgradeSuggestionService;
    private final GitHubIntegrationService gitHubIntegrationService;
    private final RepositoryRepository repositoryRepository;
    private final BuildVerificationService buildVerificationService;

    @GetMapping
    public ResponseEntity<List<UpgradeResponse>> getAllUpgrades(
            @RequestParam(required = false) Long repoId,
            @RequestParam(required = false) String riskLevel) {
        List<UpgradeSuggestionRecord> records;
        if (repoId != null) {
            records = upgradeSuggestionService.getUpgradesByRepo(repoId);
        } else {
            records = upgradeSuggestionService.getAllUpgrades();
        }

        if (riskLevel != null && !riskLevel.equalsIgnoreCase("ALL")) {
            records = records.stream()
                    .filter(r -> r.getRiskLevel().name().equalsIgnoreCase(riskLevel))
                    .collect(Collectors.toList());
        }

        List<UpgradeResponse> responses = records.stream()
                .map(this::toResponse)
                .collect(Collectors.toList());
        return ResponseEntity.ok(responses);
    }

    @PostMapping("/batch-pr")
    public ResponseEntity<Map<String, Object>> createBatchPR(@RequestBody BatchPRRequest request) {
        List<String> prUrls = new ArrayList<>();
        List<String> errors = new ArrayList<>();

        for (Long upgradeId : request.getUpgradeIds()) {
            try {
                List<UpgradeSuggestionRecord> allUpgrades = upgradeSuggestionService.getAllUpgrades();
                UpgradeSuggestionRecord upgrade = allUpgrades.stream()
                        .filter(u -> u.getId().equals(upgradeId))
                        .findFirst()
                        .orElseThrow(() -> new IllegalArgumentException("Upgrade not found: " + upgradeId));

                Repository repo = repositoryRepository.findById(upgrade.getRepoId())
                        .orElseThrow(() -> new IllegalArgumentException("Repository not found"));

                String[] parts = repo.getFullName().split("/");
                String owner = parts[0];
                String repoName = parts[1];

                String prUrl = gitHubIntegrationService.createUpgradePR(
                        owner, repoName, repo.getDefaultBranch(),
                        repo.getBuildTool().name().equals("MAVEN") ? "pom.xml" : "build.gradle",
                        "", upgrade.getGroupId(), upgrade.getArtifactId(),
                        upgrade.getCurrentVersion(), upgrade.getTargetVersion()
                );
                prUrls.add(prUrl);
            } catch (Exception e) {
                errors.add("Upgrade " + upgradeId + ": " + e.getMessage());
            }
        }

        return ResponseEntity.ok(Map.of(
                "createdPRs", prUrls,
                "errors", errors,
                "totalRequested", request.getUpgradeIds().size(),
                "successCount", prUrls.size()
        ));
    }

    @PostMapping("/batch-pr/verify")
    public ResponseEntity<Map<String, Object>> verifyAndCreateBatchPR(@RequestBody BatchPRRequest request) {
        Map<String, Object> result = new HashMap<>();

        List<Long> allUpgradeIds = request.getUpgradeIds();
        if (allUpgradeIds.isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", "No upgrades provided"
            ));
        }

        Map<Long, List<Long>> upgradesByRepo = new HashMap<>();
        for (Long upgradeId : allUpgradeIds) {
            upgradeSuggestionService.getAllUpgrades().stream()
                    .filter(u -> u.getId().equals(upgradeId))
                    .findFirst()
                    .ifPresent(u -> {
                        upgradesByRepo.computeIfAbsent(u.getRepoId(), k -> new ArrayList<>())
                                .add(upgradeId);
                    });
        }

        Map<Long, BuildVerificationService.BuildVerificationResult> verificationResults = new HashMap<>();
        List<Long> verifiedUpgradeIds = new ArrayList<>();

        for (Map.Entry<Long, List<Long>> entry : upgradesByRepo.entrySet()) {
            BuildVerificationService.BuildVerificationResult verifyResult =
                    buildVerificationService.verifyBuildSync(entry.getKey(), entry.getValue());
            verificationResults.put(entry.getKey(), verifyResult);

            if (verifyResult.isVerified()) {
                verifiedUpgradeIds.addAll(entry.getValue());
            }
        }

        result.put("verificationResults", verificationResults.values());
        result.put("verifiedCount", verifiedUpgradeIds.size());
        result.put("failedCount", allUpgradeIds.size() - verifiedUpgradeIds.size());

        if (!verifiedUpgradeIds.isEmpty() && request.isAutoCreatePR()) {
            BatchPRRequest prRequest = new BatchPRRequest();
            prRequest.setUpgradeIds(verifiedUpgradeIds);
            ResponseEntity<Map<String, Object>> prResponse = createBatchPR(prRequest);
            result.put("prResult", prResponse.getBody());
        }

        return ResponseEntity.ok(result);
    }

    @PostMapping("/verify/{repoId}")
    public ResponseEntity<BuildVerificationService.BuildVerificationResult> verifyBuild(
            @PathVariable Long repoId,
            @RequestBody List<Long> upgradeIds) {
        BuildVerificationService.BuildVerificationResult result =
                buildVerificationService.verifyBuildSync(repoId, upgradeIds);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/verify/async/{repoId}")
    public ResponseEntity<Map<String, String>> verifyBuildAsync(
            @PathVariable Long repoId,
            @RequestBody List<Long> upgradeIds) {
        CompletableFuture<BuildVerificationService.BuildVerificationResult> future =
                buildVerificationService.verifyBuildAsync(repoId, upgradeIds);

        String buildId = UUID.randomUUID().toString().substring(0, 8);
        return ResponseEntity.accepted().body(Map.of(
                "buildId", buildId,
                "message", "Build verification started"
        ));
    }

    @GetMapping("/verify/status/{buildId}")
    public ResponseEntity<BuildVerificationService.BuildVerificationResult> getVerificationStatus(
            @PathVariable String buildId) {
        BuildVerificationService.BuildVerificationResult result =
                buildVerificationService.getVerificationStatus(buildId);

        if (result == null) {
            return ResponseEntity.notFound().build();
        }

        return ResponseEntity.ok(result);
    }

    @GetMapping("/compatibility/{groupId}/{artifactId}")
    public ResponseEntity<CompatibilityResponse> checkCompatibility(
            @PathVariable String groupId,
            @PathVariable String artifactId,
            @RequestParam String currentVersion,
            @RequestParam String latestVersion) {

        UpgradeSuggestionService.CompatibilityResult result =
                upgradeSuggestionService.checkCompatibility(groupId, artifactId, currentVersion, latestVersion);

        CompatibilityResponse response = new CompatibilityResponse(
                result.groupId(), result.artifactId(), result.currentVersion(),
                result.latestVersion(), result.upgradeType().name(),
                result.compatibilityScore(), result.riskLevel().name(),
                result.breakingChanges()
        );

        return ResponseEntity.ok(response);
    }

    private UpgradeResponse toResponse(UpgradeSuggestionRecord u) {
        return new UpgradeResponse(
                u.getId(), u.getRepoId(), u.getGroupId(), u.getArtifactId(),
                u.getCurrentVersion(), u.getTargetVersion(), u.getUpgradeType(),
                u.getRiskLevel(), u.getCompatibilityScore(), u.getBreakingChanges()
        );
    }
}
