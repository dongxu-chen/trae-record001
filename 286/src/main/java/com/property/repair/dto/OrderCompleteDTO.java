package com.property.repair.dto;

import lombok.Data;
import javax.validation.constraints.NotNull;

@Data
public class OrderCompleteDTO {

    @NotNull(message = "工单ID不能为空")
    private Long orderId;

    @NotNull(message = "实际耗时不能为空")
    private Integer actualHours;

    private String feedBack;
}
