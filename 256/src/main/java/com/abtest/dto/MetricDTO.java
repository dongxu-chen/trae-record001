package com.abtest.dto;

import com.abtest.entity.Metric;
import jakarta.validation.constraints.*;
import lombok.Data;

@Data
public class MetricDTO {

    @NotBlank(message = "指标名称不能为空")
    @Size(max = 100, message = "指标名称长度不能超过100")
    private String name;

    @Size(max = 1000, message = "描述长度不能超过1000")
    private String description;

    @NotNull(message = "指标类型不能为空")
    private Metric.MetricType type;

    @NotBlank(message = "事件名称不能为空")
    private String eventName;

    private String propertyName;

    private Metric.AggregationType aggregationType;
}
