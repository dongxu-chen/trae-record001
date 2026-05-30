package com.apiversion.compare.service.impl;

import com.apiversion.compare.dto.CompatibilityReport;
import com.apiversion.compare.dto.DiffItem;
import com.apiversion.compare.dto.DiffResponse;
import com.apiversion.compare.entity.ApiVersion;
import com.apiversion.compare.mapper.ApiVersionMapper;
import com.apiversion.compare.service.CompatibilityService;
import com.apiversion.compare.service.CompareService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class CompatibilityServiceImpl implements CompatibilityService {

    private final CompareService compareService;
    private final ApiVersionMapper apiVersionMapper;

    private static final int FULL_COMPATIBILITY_THRESHOLD = 90;
    private static final int PARTIAL_COMPATIBILITY_THRESHOLD = 60;

    private static final Map<String, Integer> BREAKING_CHANGE_WEIGHTS = new HashMap<>();
    private static final Map<String, Integer> BACKWARD_COMPATIBLE_BONUS = new HashMap<>();

    static {
        BREAKING_CHANGE_WEIGHTS.put("ENDPOINT_DELETE", 30);
        BREAKING_CHANGE_WEIGHTS.put("ENDPOINT_MODIFY", 18);
        BREAKING_CHANGE_WEIGHTS.put("PARAM_DELETE", 25);
        BREAKING_CHANGE_WEIGHTS.put("PARAM_MODIFY_TYPE", 15);
        BREAKING_CHANGE_WEIGHTS.put("PARAM_MODIFY_REQUIRED", 20);
        BREAKING_CHANGE_WEIGHTS.put("RESPONSE_DELETE", 22);
        BREAKING_CHANGE_WEIGHTS.put("RESPONSE_MODIFY_TYPE", 18);
        BREAKING_CHANGE_WEIGHTS.put("RESPONSE_MODIFY_REQUIRED", 15);
        BREAKING_CHANGE_WEIGHTS.put("SCHEMA_DELETE", 18);
        BREAKING_CHANGE_WEIGHTS.put("SCHEMA_MODIFY_TYPE", 12);
        BREAKING_CHANGE_WEIGHTS.put("ENUM_REDUCED", 20);

        BACKWARD_COMPATIBLE_BONUS.put("TYPE_COMPATIBLE", 5);
        BACKWARD_COMPATIBLE_BONUS.put("ENUM_ADDED", 3);
        BACKWARD_COMPATIBLE_BONUS.put("CONSTRAINT_RELAXED", 4);
        BACKWARD_COMPATIBLE_BONUS.put("RESPONSE_HEADER_ADDED", 2);
        BACKWARD_COMPATIBLE_BONUS.put("OPTIONAL_PARAM_ADDED", 3);
    }

    @Override
    public CompatibilityReport checkCompatibility(Long sourceVersionId, Long targetVersionId) {
        ApiVersion sourceVersion = apiVersionMapper.selectById(sourceVersionId);
        ApiVersion targetVersion = apiVersionMapper.selectById(targetVersionId);

        if (sourceVersion == null || targetVersion == null) {
            throw new IllegalArgumentException("版本不存在");
        }

        DiffResponse diffResponse = compareService.compareVersions(sourceVersionId, targetVersionId);
        CompatibilityReport report = generateReport(diffResponse);
        report.setSourceVersionId(sourceVersionId);
        report.setTargetVersionId(targetVersionId);
        report.setSourceVersion(sourceVersion.getVersion());
        report.setTargetVersion(targetVersion.getVersion());

        return report;
    }

    @Override
    public CompatibilityReport generateReport(DiffResponse diffResponse) {
        CompatibilityReport report = new CompatibilityReport();

        List<DiffItem> breakingChanges = new ArrayList<>();
        List<DiffItem> compatibleChanges = new ArrayList<>();
        List<DiffItem> backwardCompatibleChanges = new ArrayList<>();

        if (diffResponse.getDifferences() != null) {
            for (DiffItem item : diffResponse.getDifferences()) {
                if (Boolean.TRUE.equals(item.getBreakingChange())) {
                    breakingChanges.add(item);
                } else if (isBackwardCompatible(item)) {
                    backwardCompatibleChanges.add(item);
                } else {
                    compatibleChanges.add(item);
                }
            }
        }

        int backwardCompatibilityScore = calculateBackwardCompatibilityScore(
                breakingChanges, backwardCompatibleChanges, diffResponse);
        int overallScore = calculateOverallCompatibilityScore(
                diffResponse, breakingChanges, backwardCompatibleChanges);
        String level = determineCompatibilityLevel(overallScore);
        String backwardLevel = determineBackwardCompatibilityLevel(backwardCompatibilityScore);

        report.setCompatibilityScore(overallScore);
        report.setBackwardCompatibilityScore(backwardCompatibilityScore);
        report.setCompatibilityLevel(level);
        report.setBackwardCompatibilityLevel(backwardLevel);
        report.setCompatible("FULL".equals(level) || "PARTIAL".equals(level));
        report.setBreakingChanges(breakingChanges);
        report.setCompatibleChanges(compatibleChanges);
        report.setBackwardCompatibleChanges(backwardCompatibleChanges);
        report.setUpgradeRecommendation(generateUpgradeRecommendation(report));
        report.setBackwardCompatibilityAnalysis(generateBackwardCompatibilityAnalysis(report));
        report.setAffectedClients(estimateAffectedClients(breakingChanges));
        report.setMigrationComplexity(estimateMigrationComplexity(breakingChanges, backwardCompatibleChanges));
        report.setGeneratedAt(LocalDateTime.now());

        return report;
    }

    private boolean isBackwardCompatible(DiffItem item) {
        String description = item.getDescription();
        return description != null && description.contains("向后兼容");
    }

    private int calculateBackwardCompatibilityScore(List<DiffItem> breakingChanges,
                                                    List<DiffItem> backwardCompatibleChanges,
                                                    DiffResponse diffResponse) {
        if (breakingChanges.isEmpty() && backwardCompatibleChanges.isEmpty()) {
            return 100;
        }

        int baseScore = 100;
        int penalty = 0;
        int bonus = 0;

        for (DiffItem item : breakingChanges) {
            penalty += getBreakingChangeWeight(item);
        }

        for (DiffItem item : backwardCompatibleChanges) {
            bonus += getBackwardCompatibleBonus(item);
        }

        int responseDeletions = (int) breakingChanges.stream()
                .filter(item -> "RESPONSE".equals(item.getDiffType()))
                .filter(item -> "DELETE".equals(item.getChangeType()))
                .count();
        penalty += responseDeletions * 5;

        int responseTypeChanges = (int) breakingChanges.stream()
                .filter(item -> "RESPONSE".equals(item.getDiffType()))
                .filter(item -> "MODIFY".equals(item.getChangeType()))
                .filter(item -> item.getDescription() != null && item.getDescription().contains("类型变更"))
                .count();
        penalty += responseTypeChanges * 8;

        return Math.max(0, Math.min(100, baseScore - penalty + bonus));
    }

    private int calculateOverallCompatibilityScore(DiffResponse diffResponse,
                                                    List<DiffItem> breakingChanges,
                                                    List<DiffItem> backwardCompatibleChanges) {
        int totalChanges = diffResponse.getTotalChanges() == null ? 0 : diffResponse.getTotalChanges();
        int breakingCount = breakingChanges.size();

        if (totalChanges == 0) {
            return 100;
        }

        int baseScore = 100;
        int penalty = 0;

        for (DiffItem item : breakingChanges) {
            penalty += getBreakingChangeWeight(item);
        }

        int backwardBonus = backwardCompatibleChanges.size() * 2;

        return Math.max(0, Math.min(100, baseScore - penalty + backwardBonus));
    }

    private int getBreakingChangeWeight(DiffItem item) {
        String key = item.getDiffType() + "_" + item.getChangeType();
        Integer weight = BREAKING_CHANGE_WEIGHTS.get(key);

        if (weight == null) {
            weight = BREAKING_CHANGE_WEIGHTS.getOrDefault(item.getDiffType() + "_MODIFY", 10);
        }

        if (item.getDescription() != null && item.getDescription().contains("不兼容")) {
            weight = (int) (weight * 1.2);
        }

        return weight;
    }

    private int getBackwardCompatibleBonus(DiffItem item) {
        String description = item.getDescription();
        if (description == null) {
            return 2;
        }

        for (Map.Entry<String, Integer> entry : BACKWARD_COMPATIBLE_BONUS.entrySet()) {
            if (description.contains(entry.getKey().replace("_", " ")) ||
                description.contains(entry.getKey())) {
                return entry.getValue();
            }
        }

        return 2;
    }

    private String determineBackwardCompatibilityLevel(int score) {
        if (score >= 90) {
            return "EXCELLENT";
        } else if (score >= 75) {
            return "GOOD";
        } else if (score >= 60) {
            return "MODERATE";
        } else if (score >= 40) {
            return "POOR";
        } else {
            return "CRITICAL";
        }
    }

    private String determineCompatibilityLevel(int score) {
        if (score >= FULL_COMPATIBILITY_THRESHOLD) {
            return "FULL";
        } else if (score >= PARTIAL_COMPATIBILITY_THRESHOLD) {
            return "PARTIAL";
        } else {
            return "NONE";
        }
    }

    private String generateBackwardCompatibilityAnalysis(CompatibilityReport report) {
        StringBuilder sb = new StringBuilder();
        String backwardLevel = report.getBackwardCompatibilityLevel();
        int backwardScore = report.getBackwardCompatibilityScore();

        sb.append("向后兼容性评估 (得分: ").append(backwardScore).append("分)\n");
        sb.append("等级: ").append(getBackwardLevelDescription(backwardLevel)).append("\n\n");

        switch (backwardLevel) {
            case "EXCELLENT":
                sb.append("✅ 向后兼容性优秀。\n");
                sb.append("  - 现有客户端可以无缝升级，无需任何修改。\n");
                sb.append("  - 所有变更都是向后兼容的。\n");
                break;
            case "GOOD":
                sb.append("👍 向后兼容性良好。\n");
                sb.append("  - 大部分现有客户端可以正常工作。\n");
                sb.append("  - 建议关注少数可能受影响的边缘场景。\n");
                break;
            case "MODERATE":
                sb.append("⚠️ 向后兼容性一般。\n");
                sb.append("  - 部分客户端可能需要调整代码。\n");
                sb.append("  - 建议进行充分的回归测试。\n");
                break;
            case "POOR":
                sb.append("⚠️ 向后兼容性较差。\n");
                sb.append("  - 较多客户端会受到影响。\n");
                sb.append("  - 建议提供明确的迁移指南。\n");
                break;
            case "CRITICAL":
                sb.append("❌ 向后兼容性严重不足。\n");
                sb.append("  - 几乎所有客户端都需要修改。\n");
                sb.append("  - 强烈建议延长旧版本支持周期。\n");
                break;
        }

        List<DiffItem> backwardChanges = report.getBackwardCompatibleChanges();
        if (backwardChanges != null && !backwardChanges.isEmpty()) {
            sb.append("\n向后兼容的变更 (").append(backwardChanges.size()).append("项):\n");
            for (int i = 0; i < Math.min(backwardChanges.size(), 5); i++) {
                DiffItem item = backwardChanges.get(i);
                sb.append("  ").append(i + 1).append(". ").append(item.getDescription()).append("\n");
            }
            if (backwardChanges.size() > 5) {
                sb.append("  ... 还有 ").append(backwardChanges.size() - 5).append(" 项向后兼容变更\n");
            }
        }

        List<DiffItem> responseChanges = report.getBreakingChanges() != null ?
                report.getBreakingChanges().stream()
                        .filter(item -> "RESPONSE".equals(item.getDiffType()))
                        .collect(Collectors.toList()) : Collections.emptyList();
        if (!responseChanges.isEmpty()) {
            sb.append("\n需要特别关注的返回值变更 (").append(responseChanges.size()).append("项):\n");
            for (int i = 0; i < Math.min(responseChanges.size(), 3); i++) {
                DiffItem item = responseChanges.get(i);
                sb.append("  ").append(i + 1).append(". ").append(item.getDescription()).append("\n");
                sb.append("     旧值: ").append(item.getOldValue()).append("\n");
                sb.append("     新值: ").append(item.getNewValue()).append("\n");
            }
        }

        return sb.toString();
    }

    private String getBackwardLevelDescription(String level) {
        switch (level) {
            case "EXCELLENT": return "优秀";
            case "GOOD": return "良好";
            case "MODERATE": return "一般";
            case "POOR": return "较差";
            case "CRITICAL": return "严重";
            default: return "未知";
        }
    }

    @Override
    public String generateUpgradeRecommendation(CompatibilityReport report) {
        StringBuilder sb = new StringBuilder();

        String level = report.getCompatibilityLevel();
        String backwardLevel = report.getBackwardCompatibilityLevel();
        int breakingCount = report.getBreakingChanges() != null ? report.getBreakingChanges().size() : 0;
        int backwardCount = report.getBackwardCompatibleChanges() != null ? report.getBackwardCompatibleChanges().size() : 0;

        sb.append("升级建议：\n");
        sb.append("综合兼容性: ").append(level).append(" (").append(report.getCompatibilityScore()).append("分)\n");
        sb.append("向后兼容性: ").append(getBackwardLevelDescription(backwardLevel))
                .append(" (").append(report.getBackwardCompatibilityScore()).append("分)\n\n");

        switch (level) {
            case "FULL":
                if (breakingCount == 0) {
                    sb.append("✅ 两个版本完全兼容，可以直接升级。\n");
                    sb.append("建议：\n");
                    sb.append("1. 可以进行平滑升级，无需修改客户端代码。\n");
                    sb.append("2. 建议先进行灰度发布，逐步切换流量。\n");
                    if (backwardCount > 0) {
                        sb.append("3. 新增 ").append(backwardCount).append(" 项向后兼容的功能，建议客户端逐步适配。\n");
                    }
                } else {
                    sb.append("⚠️ 基本兼容，但存在少量破坏性变更。\n");
                    sb.append("建议：\n");
                    sb.append("1. 建议评估受影响的客户端进行相应修改。\n");
                    sb.append("2. 建议采用分批限流推送策略，按用户群组逐步升级。\n");
                }
                break;

            case "PARTIAL":
                sb.append("⚠️ 部分兼容，升级需要谨慎。\n");
                sb.append("建议：\n");
                sb.append("1. 建议客户端进行必要的代码修改以适配变更。\n");
                sb.append("2. 强烈建议采用分批限流推送策略，控制推送速率。\n");
                sb.append("3. 建议推送批次: 内部测试 → 10%用户 → 30%用户 → 50%用户 → 全量。\n");
                sb.append("4. 每批次间隔建议不少于24小时，监控错误率和性能指标。\n");
                break;

            case "NONE":
                sb.append("❌ 存在大量破坏性变更，不兼容。\n");
                sb.append("建议：\n");
                sb.append("1. 强烈建议客户端进行全面的代码重构。\n");
                sb.append("2. 建议两个版本并行运行至少3个月。\n");
                sb.append("3. 提供详细的迁移文档和代码示例。\n");
                sb.append("4. 采用极慢的推送节奏，按租户/地域分批推送。\n");
                sb.append("5. 建立快速回滚机制，确保出现问题能及时恢复。\n");
                break;
        }

        if (breakingCount > 0) {
            sb.append("\n需要关注的破坏性变更（按影响权重排序）：\n");
            List<DiffItem> sortedBreaking = sortBreakingChangesByImpact(report.getBreakingChanges());
            for (int i = 0; i < Math.min(sortedBreaking.size(), 5); i++) {
                DiffItem item = sortedBreaking.get(i);
                sb.append(String.format("%d. [权重%d分] %s\n", i + 1,
                        getBreakingChangeWeight(item), item.getDescription()));
            }
            if (sortedBreaking.size() > 5) {
                sb.append(String.format("... 还有 %d 项破坏性变更\n", sortedBreaking.size() - 5));
            }
        }

        int compatibleCount = report.getCompatibleChanges() != null ? report.getCompatibleChanges().size() : 0;
        if (compatibleCount + backwardCount > 0) {
            sb.append("\n兼容性变更统计：\n");
            sb.append(String.format("  向后兼容新增功能：%d 项\n", backwardCount));
            sb.append(String.format("  其他非破坏性变更：%d 项\n", compatibleCount));
            sb.append("这些变更不会影响现有客户端功能，但建议逐步适配以利用新特性。\n");
        }

        sb.append("\n分批限流推送建议：\n");
        sb.append(generateRateLimitingRecommendation(report));

        return sb.toString();
    }

    private List<DiffItem> sortBreakingChangesByImpact(List<DiffItem> changes) {
        if (changes == null) {
            return Collections.emptyList();
        }
        return changes.stream()
                .sorted((a, b) -> Integer.compare(getBreakingChangeWeight(b), getBreakingChangeWeight(a)))
                .collect(Collectors.toList());
    }

    private String generateRateLimitingRecommendation(CompatibilityReport report) {
        StringBuilder sb = new StringBuilder();
        String level = report.getCompatibilityLevel();
        int migrationComplexity = report.getMigrationComplexity();

        int batchSize;
        int intervalHours;
        int totalBatches;

        switch (level) {
            case "FULL":
                batchSize = 100;
                intervalHours = 1;
                totalBatches = 1;
                break;
            case "PARTIAL":
                batchSize = 10;
                intervalHours = 24;
                totalBatches = 10;
                break;
            case "NONE":
                batchSize = 5;
                intervalHours = 48;
                totalBatches = 20;
                break;
            default:
                batchSize = 20;
                intervalHours = 12;
                totalBatches = 5;
        }

        if (migrationComplexity > 70) {
            batchSize = Math.max(1, batchSize / 2);
            intervalHours *= 2;
            totalBatches *= 2;
        }

        sb.append(String.format("  推荐每批推送比例: %d%%\n", batchSize));
        sb.append(String.format("  推荐批次间隔: %d小时\n", intervalHours));
        sb.append(String.format("  预计总批次数: %d批\n", totalBatches));
        sb.append(String.format("  预计完成时间: %d天\n", (totalBatches * intervalHours) / 24));
        sb.append("  阈值配置:\n");
        sb.append("    - 错误率 > 1%: 暂停推送，排查问题\n");
        sb.append("    - 响应时间增加 > 20%: 评估性能影响\n");
        sb.append("    - 用户投诉 > 5起/小时: 启动回滚流程\n");

        return sb.toString();
    }

    private int estimateMigrationComplexity(List<DiffItem> breakingChanges,
                                            List<DiffItem> backwardCompatibleChanges) {
        if (breakingChanges == null || breakingChanges.isEmpty()) {
            return 0;
        }

        int totalWeight = breakingChanges.stream()
                .mapToInt(this::getBreakingChangeWeight)
                .sum();

        int bonus = backwardCompatibleChanges != null ? backwardCompatibleChanges.size() * 2 : 0;

        return Math.min(100, Math.max(0, totalWeight - bonus));
    }

    private int estimateAffectedClients(List<DiffItem> breakingChanges) {
        if (breakingChanges == null || breakingChanges.isEmpty()) {
            return 0;
        }

        int endpointDeletions = (int) breakingChanges.stream()
                .filter(item -> "ENDPOINT".equals(item.getDiffType()))
                .filter(item -> "DELETE".equals(item.getChangeType()))
                .count();

        int paramDeletions = (int) breakingChanges.stream()
                .filter(item -> "PARAM".equals(item.getDiffType()))
                .filter(item -> "DELETE".equals(item.getChangeType()))
                .count();

        int schemaDeletions = (int) breakingChanges.stream()
                .filter(item -> "SCHEMA".equals(item.getDiffType()))
                .filter(item -> "DELETE".equals(item.getChangeType()))
                .count();

        int responseTypeChanges = (int) breakingChanges.stream()
                .filter(item -> "RESPONSE".equals(item.getDiffType()))
                .filter(item -> "MODIFY".equals(item.getChangeType()))
                .filter(item -> item.getDescription() != null && item.getDescription().contains("类型变更"))
                .count();

        return endpointDeletions * 15 + paramDeletions * 8 + schemaDeletions * 5 + responseTypeChanges * 10;
    }
}
