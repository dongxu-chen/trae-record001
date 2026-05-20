package com.smartschedule.planner;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ConstraintWeights {
    private int requiredSkillMatch;
    private int noOverlappingShifts;
    private int maxDailyHours;
    private int maxWeeklyHours;
    private int minWeeklyHours;
    private int unavailableDays;
    private int maxConsecutiveDays;
    private int maxConsecutiveNightShifts;
    private int unwantedShiftTypes;
    private int preferredShiftTypes;
    private int balancedWorkload;
    private int shiftRotation;
    private int assignEveryShift;
    private int maxConsecutiveNightShiftsLimit;
}
