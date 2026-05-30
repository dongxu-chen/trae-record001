package com.apiversion.version.entity;

import com.baomidou.mybatisplus.annotation.*;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("gray_policy")
@Schema(description = "灰度策略")
public class GrayPolicy {

    @TableId(type = IdType.AUTO)
    @Schema(description = "策略ID")
    private Long id;

    @Schema(description = "版本ID")
    private Long versionId;

    @Schema(description = "策略名称")
    private String policyName;

    @Schema(description = "灰度百分比")
    private Integer grayPercent;

    @Schema(description = "灰度用户列表")
    private String grayUsers;

    @Schema(description = "灰度IP列表")
    private String grayIps;

    @Schema(description = "灰度标签")
    private String grayTags;

    @Schema(description = "开始时间")
    private LocalDateTime startTime;

    @Schema(description = "结束时间")
    private LocalDateTime endTime;

    @Schema(description = "是否启用")
    private Boolean enabled;

    @Schema(description = "创建时间")
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @Schema(description = "更新时间")
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @Schema(description = "是否删除")
    @TableLogic
    private Integer deleted;
}
