package com.smartschedule.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "schedule.constraint.weights")
public class ConstraintWeightConfig {

    private int requiredSkillMatch = 1000;
    private int noOverlappingShifts = 500;
    private int maxDailyHours = 200;
    private int maxWeeklyHours = 100;
    private int minWeeklyHours = 50;
    private int unavailableDays = 1000;
    private int maxConsecutiveDays = 300;
    private int maxConsecutiveNightShifts = 800;
    private int unwantedShiftTypes = 20;
    private int preferredShiftTypes = 10;
    private int balancedWorkload = 5;
    private int shiftRotation = 15;
    private int assignEveryShift = 200;

    private int maxConsecutiveNightShiftsLimit = 2;

    public void updateWeights(ConstraintWeightConfig newConfig) {
        this.requiredSkillMatch = newConfig.requiredSkillMatch;
        this.noOverlappingShifts = newConfig.noOverlappingShifts;
        this.maxDailyHours = newConfig.maxDailyHours;
        this.maxWeeklyHours = newConfig.maxWeeklyHours;
        this.minWeeklyHours = newConfig.minWeeklyHours;
        this.unavailableDays = newConfig.unavailableDays;
        this.maxConsecutiveDays = newConfig.maxConsecutiveDays;
        this.maxConsecutiveNightShifts = newConfig.maxConsecutiveNightShifts;
        this.unwantedShiftTypes = newConfig.unwantedShiftTypes;
        this.preferredShiftTypes = newConfig.preferredShiftTypes;
        this.balancedWorkload = newConfig.balancedWorkload;
        this.shiftRotation = newConfig.shiftRotation;
        this.assignEveryShift = newConfig.assignEveryShift;
        this.maxConsecutiveNightShiftsLimit = newConfig.maxConsecutiveNightShiftsLimit;
    }
}
