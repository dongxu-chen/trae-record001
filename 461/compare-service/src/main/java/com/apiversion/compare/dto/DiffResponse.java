package com.apiversion.compare.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Schema(description = "差异对比响应")
public class DiffResponse {

    @Schema(description = "对比ID")
    private Long id;

    @Schema(description = "源版本ID")
    private Long sourceVersionId;

    @Schema(description = "目标版本ID")
    private Long targetVersionId;

    @Schema(description = "源版本号")
    private String sourceVersion;

    @Schema(description = "目标版本号")
    private String targetVersion;

    @Schema(description = "差异总数")
    private Integer totalChanges;

    @Schema(description = "新增数量")
    private Integer addedCount;

    @Schema(description = "删除数量")
    private Integer deletedCount;

    @Schema(description = "修改数量")
    private Integer modifiedCount;

    @Schema(description = "破坏性变更数量")
    private Integer breakingChangesCount;

    @Schema(description = "是否兼容")
    private Boolean compatible;

    @Schema(description = "差异列表")
    private List<DiffItem> differences;

    @Schema(description = "对比时间")
    private LocalDateTime compareTime;
}
