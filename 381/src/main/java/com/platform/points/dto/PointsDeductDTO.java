package com.platform.points.dto;

import lombok.Data;

import javax.validation.constraints.Min;
import javax.validation.constraints.NotNull;

@Data
public class PointsDeductDTO {

    @NotNull(message = "用户ID不能为空")
    private Long userId;

    @NotNull(message = "积分数额不能为空")
    @Min(value = 1, message = "积分必须大于0")
    private Integer points;

    @NotNull(message = "积分来源不能为空")
    private Integer source;

    private String orderNo;

    private String description;

    private String remark;
}
