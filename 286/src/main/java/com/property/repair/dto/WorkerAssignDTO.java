package com.property.repair.dto;

import lombok.Data;
import javax.validation.constraints.NotNull;

@Data
public class WorkerAssignDTO {

    @NotNull(message = "工单ID不能为空")
    private Long orderId;

    @NotNull(message = "维修工ID不能为空")
    private Long workerId;
}
