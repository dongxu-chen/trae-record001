package com.apiversion.version.entity;

import com.baomidou.mybatisplus.annotation.*;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("diff_result")
@Schema(description = "差异对比结果")
public class DiffResult {

    @TableId(type = IdType.AUTO)
    @Schema(description = "对比ID")
    private Long id;

    @Schema(description = "源版本ID")
    private Long sourceVersionId;

    @Schema(description = "目标版本ID")
    private Long targetVersionId;

    @Schema(description = "对比类型：ENDPOINT, PARAM, RESPONSE")
    private String diffType;

    @Schema(description = "变更类型：ADD, DELETE, MODIFY")
    private String changeType;

    @Schema(description = "变更路径")
    private String changePath;

    @Schema(description = "变更前内容")
    private String oldValue;

    @Schema(description = "变更后内容")
    private String newValue;

    @Schema(description = "是否兼容")
    private Boolean compatible;

    @Schema(description = "创建时间")
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @Schema(description = "是否删除")
    @TableLogic
    private Integer deleted;
}
