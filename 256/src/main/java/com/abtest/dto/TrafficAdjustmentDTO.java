package com.abtest.dto;

import jakarta.validation.constraints.*;
import lombok.Data;

@Data
public class TrafficAdjustmentDTO {

    @NotNull(message = "实验ID不能为空")
    private Long experimentId;

    @NotNull(message = "新的流量占比不能为空")
    @Min(value = 1, message = "流量占比最小为1%")
    @Max(value = 100, message = "流量占比最大为100%")
    private Integer newTrafficPercentage;
}
