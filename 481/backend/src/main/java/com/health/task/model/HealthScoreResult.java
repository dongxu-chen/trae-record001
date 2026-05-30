package com.health.task.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class HealthScoreResult {
    private String taskName;
    private String taskGroup;
    private int overallScore;
    private List<DimensionScore> dimensionScores;
    private String diagnosis;
    private String suggestion;
}
