package com.health.task.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class WeightConfigRequest {
    private String taskName;
    private String taskGroup;
    private String importanceLevel;
    private Double durationWeight;
    private Double successRateWeight;
    private Double frequencyWeight;
    private Double resourceWeight;
    private String description;
}
