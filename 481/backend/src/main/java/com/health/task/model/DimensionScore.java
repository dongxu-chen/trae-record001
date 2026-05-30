package com.health.task.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DimensionScore {
    private String dimensionName;
    private int score;
    private double weight;
    private double weightedScore;
    private String detail;
}
