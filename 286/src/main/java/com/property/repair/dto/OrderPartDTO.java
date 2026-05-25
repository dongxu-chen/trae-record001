package com.property.repair.dto;

import lombok.Data;
import javax.validation.constraints.NotNull;

@Data
public class OrderPartDTO {

    @NotNull(message = "工单ID不能为空")
    private Long orderId;

    @NotNull(message = "备件ID不能为空")
    private Long partId;

    @NotNull(message = "数量不能为空")
    private Integer quantity;

    private Long operatorId;

    private String operatorName;
}
