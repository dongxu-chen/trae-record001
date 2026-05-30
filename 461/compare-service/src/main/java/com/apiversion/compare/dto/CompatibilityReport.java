package com.apiversion.compare.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Schema(description = "兼容性报告")
public class CompatibilityReport {

    @Schema(description = "报告ID")
    private Long reportId;

    @Schema(description = "源版本ID")
    private Long sourceVersionId;

    @Schema(description = "目标版本ID")
    private Long targetVersionId;

    @Schema(description = "源版本号")
    private String sourceVersion;

    @Schema(description = "目标版本号")
    private String targetVersion;

    @Schema(description = "兼容性等级：FULL-完全兼容, PARTIAL-部分兼容, NONE-不兼容")
    private String compatibilityLevel;

    @Schema(description = "兼容性评分：0-100")
    private Integer compatibilityScore;

    @Schema(description = "向后兼容性评分：0-100")
    private Integer backwardCompatibilityScore;

    @Schema(description = "向后兼容性等级：EXCELLENT-优秀, GOOD-良好, MODERATE-一般, POOR-较差, CRITICAL-严重")
    private String backwardCompatibilityLevel;

    @Schema(description = "是否兼容")
    private Boolean compatible;

    @Schema(description = "破坏性变更列表")
    private List<DiffItem> breakingChanges;

    @Schema(description = "兼容变更列表")
    private List<DiffItem> compatibleChanges;

    @Schema(description = "向后兼容的变更列表")
    private List<DiffItem> backwardCompatibleChanges;

    @Schema(description = "向后兼容性分析")
    private String backwardCompatibilityAnalysis;

    @Schema(description = "迁移复杂度：0-100")
    private Integer migrationComplexity;

    @Schema(description = "升级建议")
    private String upgradeRecommendation;

    @Schema(description = "影响的客户端数量")
    private Integer affectedClients;

    @Schema(description = "报告生成时间")
    private LocalDateTime generatedAt;
}
