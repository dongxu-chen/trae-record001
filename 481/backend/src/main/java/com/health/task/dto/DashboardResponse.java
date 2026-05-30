package com.health.task.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DashboardResponse {
    private int totalTasks;
    private double avgScore;
    private int healthyCount;
    private int warningCount;
    private int criticalCount;
    private List<HealthScoreResponse> taskScores;
}
