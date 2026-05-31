package com.depguard.service;

import com.depguard.engine.BinaryCompatibilityChecker;
import com.depguard.engine.DependencyHealthScorer;
import com.depguard.entity.UpgradeSuggestionRecord;
import com.depguard.enums.RiskLevel;
import com.depguard.enums.UpgradeType;
import com.depguard.repository.UpgradeSuggestionRecordRepository;
import com.depguard.repository.RepositoryRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class AutoUpgradeService {

    private final UpgradeSuggestionRecordRepository upgradeSuggestionRepository;
    private final RepositoryRepository repositoryRepository;
    private final DependencyHealthScorer healthScorer;
    private final BinaryCompatibilityChecker compatibilityChecker;
    private final BuildVerificationService buildVerificationService;
    private final GitHubService gitHubService;

    private static final double MIN_COMPATIBILITY_SCORE = 85.0;
    private static final double MIN_HEALTH_SCORE = 70.0;
    private static final Set<RiskLevel> ALLOWED_RISK_LEVELS = EnumSet.of(RiskLevel.SAFE, RiskLevel.LOW_RISK);
    private static final Set<UpgradeType> ALLOWED_UPGRADE_TYPES = EnumSet.of(UpgradeType.PATCH, UpgradeType.MINOR);

    public AutoUpgradeResult getAutoUpgradeCandidates(Long repoId) {
        List<UpgradeSuggestionRecord> allSuggestions = upgradeSuggestionRepository.findByRepoId(repoId);

        List<UpgradeSuggestionRecord> autoUpgradeCandidates = new ArrayList<>();
        List<UpgradeSuggestionRecord> manualReviewRequired = new ArrayList<>();

        for (UpgradeSuggestionRecord suggestion : allSuggestions) {
            if (isEligibleForAutoUpgrade(suggestion)) {
                autoUpgradeCandidates.add(suggestion);
            } else {
                manualReviewRequired.add(suggestion);
            }
        }

        autoUpgradeCandidates.sort((a, b) -> {
            int scoreCompare = Double.compare(
                    b.getCompatibilityScore() != null ? b.getCompatibilityScore() : 0,
                    a.getCompatibilityScore() != null ? a.getCompatibilityScore() : 0
            );
            if (scoreCompare != 0) return scoreCompare;
            return a.getUpgradeType().compareTo(b.getUpgradeType());
        });

        Map<String, Object> summary = generateSummary(autoUpgradeCandidates, manualReviewRequired);

        return new AutoUpgradeResult(
                autoUpgradeCandidates,
                manualReviewRequired,
                summary
        );
    }

    private boolean isEligibleForAutoUpgrade(UpgradeSuggestionRecord suggestion) {
        if (!ALLOWED_UPGRADE_TYPES.contains(suggestion.getUpgradeType())) {
            return false;
        }

        if (!ALLOWED_RISK_LEVELS.contains(suggestion.getRiskLevel())) {
            return false;
        }

        Double compatibilityScore = suggestion.getCompatibilityScore();
        if (compatibilityScore == null || compatibilityScore < MIN_COMPATIBILITY_SCORE) {
            return false;
        }

        String breakingChanges = suggestion.getBreakingChanges();
        if (breakingChanges != null && !breakingChanges.isEmpty()) {
            return false;
        }

        return true;
    }

    public Map<String, Object> generateSummary(List<UpgradeSuggestionRecord> autoCandidates,
                                               List<UpgradeSuggestionRecord> manualCandidates) {
        Map<String, Object> summary = new HashMap<>();

        long patchCount = autoCandidates.stream()
                .filter(s -> s.getUpgradeType() == UpgradeType.PATCH)
                .count();
        long minorCount = autoCandidates.stream()
                .filter(s -> s.getUpgradeType() == UpgradeType.MINOR)
                .count();
        long majorCount = manualCandidates.stream()
                .filter(s -> s.getUpgradeType() == UpgradeType.MAJOR)
                .count();
        long highRiskCount = manualCandidates.stream()
                .filter(s -> s.getRiskLevel() == RiskLevel.HIGH_RISK || s.getRiskLevel() == RiskLevel.MEDIUM_RISK)
                .count();

        double avgCompatibility = autoCandidates.stream()
                .mapToDouble(s -> s.getCompatibilityScore() != null ? s.getCompatibilityScore() : 0)
                .average()
                .orElse(0.0);

        summary.put("autoUpgradeCount", autoCandidates.size());
        summary.put("manualReviewCount", manualCandidates.size());
        summary.put("patchUpgrades", patchCount);
        summary.put("minorUpgrades", minorCount);
        summary.put("majorUpgrades", majorCount);
        summary.put("highRiskCount", highRiskCount);
        summary.put("averageCompatibilityScore", Math.round(avgCompatibility * 100.0) / 100.0);
        summary.put("minCompatibilityThreshold", MIN_COMPATIBILITY_SCORE);
        summary.put("allowedUpgradeTypes", ALLOWED_UPGRADE_TYPES);
        summary.put("allowedRiskLevels", ALLOWED_RISK_LEVELS);

        return summary;
    }

    @Async
    public AutoUpgradeExecutionResult executeAutoUpgrade(Long repoId, String userId) {
        AutoUpgradeResult candidates = getAutoUpgradeCandidates(repoId);
        List<UpgradeSuggestionRecord> toUpgrade = candidates.getAutoUpgradeCandidates();

        AutoUpgradeExecutionResult result = new AutoUpgradeExecutionResult();
        result.setStartTime(LocalDateTime.now());
        result.setTotalRequested(toUpgrade.size());

        List<UpgradeResult> successes = new ArrayList<>();
        List<UpgradeResult> failures = new ArrayList<>();
        List<UpgradeResult> skipped = new ArrayList<>();

        for (UpgradeSuggestionRecord suggestion : toUpgrade) {
            try {
                UpgradeResult upgradeResult = executeSingleUpgrade(repoId, suggestion);

                if (upgradeResult.isSuccess()) {
                    successes.add(upgradeResult);
                } else if (upgradeResult.isSkipped()) {
                    skipped.add(upgradeResult);
                } else {
                    failures.add(upgradeResult);
                }
            } catch (Exception e) {
                log.error("Auto upgrade failed for {}:{}",
                        suggestion.getGroupId(), suggestion.getArtifactId(), e);
                failures.add(new UpgradeResult(
                        suggestion.getGroupId(),
                        suggestion.getArtifactId(),
                        suggestion.getCurrentVersion(),
                        suggestion.getTargetVersion(),
                        false,
                        false,
                        e.getMessage(),
                        null
                ));
            }
        }

        result.setSuccessCount(successes.size());
        result.setFailureCount(failures.size());
        result.setSkippedCount(skipped.size());
        result.setSuccesses(successes);
        result.setFailures(failures);
        result.setSkipped(skipped);
        result.setEndTime(LocalDateTime.now());

        if (!successes.isEmpty()) {
            try {
                String prUrl = createCombinedPR(repoId, successes, userId);
                result.setPrUrl(prUrl);
            } catch (Exception e) {
                log.error("Failed to create combined PR", e);
                result.setPrError(e.getMessage());
            }
        }

        return result;
    }

    private UpgradeResult executeSingleUpgrade(Long repoId, UpgradeSuggestionRecord suggestion) {
        String groupId = suggestion.getGroupId();
        String artifactId = suggestion.getArtifactId();
        String currentVersion = suggestion.getCurrentVersion();
        String targetVersion = suggestion.getTargetVersion();

        BinaryCompatibilityChecker.CompatibilityCheckResult asmResult =
                compatibilityChecker.checkBinaryCompatibility(groupId, artifactId, currentVersion, targetVersion);

        if (asmResult.getCompatibilityScore() < MIN_COMPATIBILITY_SCORE) {
            return new UpgradeResult(
                    groupId, artifactId, currentVersion, targetVersion,
                    false, true,
                    "ASM检查发现兼容性问题: " + String.join(", ", asmResult.getBreakingChanges()),
                    null
            );
        }

        BuildVerificationService.BuildVerificationResult buildResult =
                buildVerificationService.verifyBuildSync(repoId, suggestion.getId(), true);

        if (!buildResult.isSuccess()) {
            return new UpgradeResult(
                    groupId, artifactId, currentVersion, targetVersion,
                    false, false,
                    "构建验证失败: " + buildResult.getErrorMessage(),
                    buildResult
            );
        }

        return new UpgradeResult(
                groupId, artifactId, currentVersion, targetVersion,
                true, false,
                "升级成功",
                buildResult
        );
    }

    private String createCombinedPR(Long repoId, List<UpgradeResult> upgrades, String userId) {
        com.depguard.entity.Repository repo = repositoryRepository.findById(repoId)
                .orElseThrow(() -> new RuntimeException("Repository not found: " + repoId));

        StringBuilder title = new StringBuilder();
        title.append("[Auto-Upgrade] ").append(upgrades.size()).append(" 个依赖自动升级");

        StringBuilder body = new StringBuilder();
        body.append("## 自动升级变更\n\n");
        body.append("此 PR 由 DepGuard 自动升级系统生成，包含以下低风险、高兼容性的依赖升级：\n\n");

        for (UpgradeResult upgrade : upgrades) {
            body.append("- **")
                    .append(upgrade.getGroupId()).append(":").append(upgrade.getArtifactId())
                    .append("**: `")
                    .append(upgrade.getCurrentVersion()).append("` → `")
                    .append(upgrade.getTargetVersion()).append("`\n");
        }

        body.append("\n## 安全保证\n\n");
        body.append("- ✅ 所有升级均通过 ASM 二进制兼容性检查\n");
        body.append("- ✅ 所有升级均通过构建验证\n");
        body.append("- ✅ 仅包含 PATCH 和 MINOR 版本升级\n");
        body.append("- ✅ 所有升级风险等级为 SAFE 或 LOW_RISK\n\n");

        body.append("## 统计信息\n\n");
        body.append("- 升级数量: ").append(upgrades.size()).append("\n");
        body.append("- 执行时间: ").append(LocalDateTime.now()).append("\n");
        body.append("- 触发用户: ").append(userId != null ? userId : "system").append("\n");

        String branchName = "auto-upgrade/" + System.currentTimeMillis();

        return gitHubService.createPR(repo, title.toString(), body.toString(), branchName, "main");
    }

    public AutoUpgradeConfig getAutoUpgradeConfig() {
        return new AutoUpgradeConfig(
                MIN_COMPATIBILITY_SCORE,
                MIN_HEALTH_SCORE,
                new ArrayList<>(ALLOWED_UPGRADE_TYPES),
                new ArrayList<>(ALLOWED_RISK_LEVELS)
        );
    }

    @lombok.Data
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class AutoUpgradeResult {
        private List<UpgradeSuggestionRecord> autoUpgradeCandidates;
        private List<UpgradeSuggestionRecord> manualReviewRequired;
        private Map<String, Object> summary;
    }

    @lombok.Data
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class UpgradeResult {
        private String groupId;
        private String artifactId;
        private String currentVersion;
        private String targetVersion;
        private boolean success;
        private boolean skipped;
        private String message;
        private BuildVerificationService.BuildVerificationResult buildResult;
    }

    @lombok.Data
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class AutoUpgradeExecutionResult {
        private LocalDateTime startTime;
        private LocalDateTime endTime;
        private int totalRequested;
        private int successCount;
        private int failureCount;
        private int skippedCount;
        private List<UpgradeResult> successes;
        private List<UpgradeResult> failures;
        private List<UpgradeResult> skipped;
        private String prUrl;
        private String prError;
    }

    @lombok.Data
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class AutoUpgradeConfig {
        private double minCompatibilityScore;
        private double minHealthScore;
        private List<UpgradeType> allowedUpgradeTypes;
        private List<RiskLevel> allowedRiskLevels;
    }
}
