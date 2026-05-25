package com.property.repair.dto;

import lombok.Data;
import javax.validation.constraints.Max;
import javax.validation.constraints.Min;
import javax.validation.constraints.NotNull;

@Data
public class EvaluationDTO {

    @NotNull(message = "工单ID不能为空")
    private Long orderId;

    @NotNull(message = "业主ID不能为空")
    private Long ownerId;

    @NotNull(message = "评分不能为空")
    @Min(value = 1, message = "评分最小为1")
    @Max(value = 5, message = "评分最大为5")
    private Integer rating;

    private String comment;
}
