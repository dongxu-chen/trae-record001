package com.abtest.dto;

import jakarta.validation.constraints.*;
import lombok.Data;

@Data
public class VariantDTO {

    @NotBlank(message = "实验组名称不能为空")
    @Size(max = 50, message = "实验组名称长度不能超过50")
    private String name;

    @NotNull(message = "流量权重不能为空")
    @Min(value = 1, message = "流量权重最小为1")
    @Max(value = 10000, message = "流量权重最大为10000")
    private Integer trafficWeight;

    private Boolean isControl = false;

    private String configuration;
}
