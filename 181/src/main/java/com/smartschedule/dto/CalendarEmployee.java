package com.smartschedule.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CalendarEmployee {
    private Long id;
    private String name;
    private String employeeNo;
    private Integer totalHours;
    private Integer totalShifts;
}
