package com.smartschedule.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ScheduleSatisfactionAnalysis {
    private Double overallSatisfactionScore;
    private Double preferenceSatisfactionRate;
    private Double workloadFairnessScore;
    private Double conflictRate;
    private Integer totalAssignments;
    private Integer satisfiedAssignments;
    private Integer conflictingAssignments;
    private List<EmployeeSatisfaction> employeeSatisfactions;
    private Map<String, Object> fairnessMetrics;
}
