package com.smartschedule.controller;

import com.smartschedule.config.ConstraintWeightConfig;
import com.smartschedule.dto.ApiResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/constraint-weights")
@CrossOrigin(origins = "*")
public class ConstraintWeightController {

    @Autowired
    private ConstraintWeightConfig weightConfig;

    @GetMapping
    public ResponseEntity<ApiResponse<ConstraintWeightConfig>> getWeights() {
        return ResponseEntity.ok(ApiResponse.success(weightConfig));
    }

    @PutMapping
    public ResponseEntity<ApiResponse<ConstraintWeightConfig>> updateWeights(
            @RequestBody ConstraintWeightConfig newConfig) {
        weightConfig.updateWeights(newConfig);
        return ResponseEntity.ok(ApiResponse.success(weightConfig));
    }

    @GetMapping("/{name}")
    public ResponseEntity<ApiResponse<Integer>> getWeight(@PathVariable String name) {
        Integer value = getWeightValueByName(name);
        if (value == null) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error(400, "Unknown weight: " + name));
        }
        return ResponseEntity.ok(ApiResponse.success(value));
    }

    @PutMapping("/{name}")
    public ResponseEntity<ApiResponse<ConstraintWeightConfig>> updateWeight(
            @PathVariable String name,
            @RequestParam int value) {
        boolean updated = setWeightValueByName(name, value);
        if (!updated) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error(400, "Unknown weight: " + name));
        }
        return ResponseEntity.ok(ApiResponse.success(weightConfig));
    }

    private Integer getWeightValueByName(String name) {
        return switch (name) {
            case "requiredSkillMatch" -> weightConfig.getRequiredSkillMatch();
            case "noOverlappingShifts" -> weightConfig.getNoOverlappingShifts();
            case "maxDailyHours" -> weightConfig.getMaxDailyHours();
            case "maxWeeklyHours" -> weightConfig.getMaxWeeklyHours();
            case "minWeeklyHours" -> weightConfig.getMinWeeklyHours();
            case "unavailableDays" -> weightConfig.getUnavailableDays();
            case "maxConsecutiveDays" -> weightConfig.getMaxConsecutiveDays();
            case "maxConsecutiveNightShifts" -> weightConfig.getMaxConsecutiveNightShifts();
            case "maxConsecutiveNightShiftsLimit" -> weightConfig.getMaxConsecutiveNightShiftsLimit();
            case "unwantedShiftTypes" -> weightConfig.getUnwantedShiftTypes();
            case "preferredShiftTypes" -> weightConfig.getPreferredShiftTypes();
            case "balancedWorkload" -> weightConfig.getBalancedWorkload();
            case "shiftRotation" -> weightConfig.getShiftRotation();
            case "assignEveryShift" -> weightConfig.getAssignEveryShift();
            default -> null;
        };
    }

    private boolean setWeightValueByName(String name, int value) {
        return switch (name) {
            case "requiredSkillMatch" -> {
                weightConfig.setRequiredSkillMatch(value);
                yield true;
            }
            case "noOverlappingShifts" -> {
                weightConfig.setNoOverlappingShifts(value);
                yield true;
            }
            case "maxDailyHours" -> {
                weightConfig.setMaxDailyHours(value);
                yield true;
            }
            case "maxWeeklyHours" -> {
                weightConfig.setMaxWeeklyHours(value);
                yield true;
            }
            case "minWeeklyHours" -> {
                weightConfig.setMinWeeklyHours(value);
                yield true;
            }
            case "unavailableDays" -> {
                weightConfig.setUnavailableDays(value);
                yield true;
            }
            case "maxConsecutiveDays" -> {
                weightConfig.setMaxConsecutiveDays(value);
                yield true;
            }
            case "maxConsecutiveNightShifts" -> {
                weightConfig.setMaxConsecutiveNightShifts(value);
                yield true;
            }
            case "maxConsecutiveNightShiftsLimit" -> {
                weightConfig.setMaxConsecutiveNightShiftsLimit(value);
                yield true;
            }
            case "unwantedShiftTypes" -> {
                weightConfig.setUnwantedShiftTypes(value);
                yield true;
            }
            case "preferredShiftTypes" -> {
                weightConfig.setPreferredShiftTypes(value);
                yield true;
            }
            case "balancedWorkload" -> {
                weightConfig.setBalancedWorkload(value);
                yield true;
            }
            case "shiftRotation" -> {
                weightConfig.setShiftRotation(value);
                yield true;
            }
            case "assignEveryShift" -> {
                weightConfig.setAssignEveryShift(value);
                yield true;
            }
            default -> false;
        };
    }
}
