package com.smartschedule.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CalendarCell {
    private Long assignmentId;
    private Long shiftRequirementId;
    private Long shiftTypeId;
    private String shiftTypeName;
    private String shiftTypeCode;
    private LocalTime startTime;
    private LocalTime endTime;
    private String color;
    private Boolean isLocked;
    private Boolean isConflict;
    private String conflictMessage;
    private Boolean isPreferred;
    private Boolean isUnwanted;
}
