package com.abtest.dto;

import jakarta.validation.constraints.*;
import lombok.Data;

@Data
public class LayerDTO {

    @NotBlank(message = "层名称不能为空")
    @Size(max = 100, message = "层名称长度不能超过100")
    private String name;

    @Size(max = 1000, message = "描述长度不能超过1000")
    private String description;

    @NotBlank(message = "流量分流键不能为空")
    private String trafficKey;

    @Min(value = 1, message = "流量占比最小为1%")
    @Max(value = 100, message = "流量占比最大为100%")
    private Integer trafficPercentage = 100;

    private Boolean isActive = true;
}
