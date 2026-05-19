package com.smartschedule.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class EmployeeSatisfaction {
    private Long employeeId;
    private String employeeName;
    private Integer totalShifts;
    private Integer preferredShifts;
    private Integer unwantedShifts;
    private Integer totalHours;
    private Double preferenceSatisfaction;
    private Double workloadDeviation;
    private Integer conflictCount;
    private Double satisfactionScore;
}
