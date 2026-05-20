package com.smartschedule.controller;

import com.smartschedule.entity.Schedule;
import com.smartschedule.entity.ShiftAssignment;
import com.smartschedule.entity.ShiftRequirement;
import com.smartschedule.planner.ScheduleSolution;
import com.smartschedule.service.ScheduleService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/schedules")
@CrossOrigin(origins = "*")
public class ScheduleController {

    @Autowired
    private ScheduleService scheduleService;

    @PostMapping
    public ResponseEntity<Schedule> createSchedule(@RequestBody Schedule schedule) {
        return ResponseEntity.ok(scheduleService.createSchedule(schedule));
    }

    @GetMapping("/{id}")
    public ResponseEntity<Schedule> getSchedule(@PathVariable Long id) {
        return ResponseEntity.ok(scheduleService.getSchedule(id));
    }

    @GetMapping
    public ResponseEntity<List<Schedule>> getAllSchedules() {
        return ResponseEntity.ok(scheduleService.getAllSchedules());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteSchedule(@PathVariable Long id) {
        scheduleService.deleteSchedule(id);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/{scheduleId}/requirements")
    public ResponseEntity<ShiftRequirement> addShiftRequirement(
            @PathVariable Long scheduleId,
            @RequestBody ShiftRequirement requirement) {
        return ResponseEntity.ok(scheduleService.addShiftRequirement(scheduleId, requirement));
    }

    @GetMapping("/{scheduleId}/requirements")
    public ResponseEntity<List<ShiftRequirement>> getShiftRequirements(@PathVariable Long scheduleId) {
        return ResponseEntity.ok(scheduleService.getShiftRequirements(scheduleId));
    }

    @PostMapping("/{scheduleId}/generate")
    public ResponseEntity<ScheduleSolution> generateSchedule(@PathVariable Long scheduleId) {
        ScheduleSolution solution = scheduleService.generateSchedule(scheduleId);
        return ResponseEntity.ok(solution);
    }

    @GetMapping("/{scheduleId}/assignments")
    public ResponseEntity<List<ShiftAssignment>> getAssignments(@PathVariable Long scheduleId) {
        return ResponseEntity.ok(scheduleService.getAssignments(scheduleId));
    }

    @PutMapping("/assignments/{assignmentId}")
    public ResponseEntity<ShiftAssignment> updateAssignment(
            @PathVariable Long assignmentId,
            @RequestParam(required = false) Long employeeId) {
        return ResponseEntity.ok(scheduleService.updateAssignment(assignmentId, employeeId));
    }

    @PutMapping("/assignments/{assignmentId}/lock")
    public ResponseEntity<ShiftAssignment> lockAssignment(
            @PathVariable Long assignmentId,
            @RequestParam boolean locked) {
        return ResponseEntity.ok(scheduleService.lockAssignment(assignmentId, locked));
    }

    @PostMapping("/{scheduleId}/lock-before")
    public ResponseEntity<Void> lockAllAssignmentsBeforeDate(
            @PathVariable Long scheduleId,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date) {
        scheduleService.lockAllAssignmentsBeforeDate(scheduleId, date);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/{scheduleId}/recalculate")
    public ResponseEntity<ScheduleSolution> recalculateSchedule(@PathVariable Long scheduleId) {
        return ResponseEntity.ok(scheduleService.recalculateSchedule(scheduleId));
    }

    @PostMapping("/{scheduleId}/incremental-recalculate")
    public ResponseEntity<ScheduleSolution> incrementalRecalculate(@PathVariable Long scheduleId) {
        return ResponseEntity.ok(scheduleService.incrementalRecalculate(scheduleId));
    }

    @GetMapping("/{scheduleId}/statistics")
    public ResponseEntity<Map<String, Object>> getScheduleStatistics(@PathVariable Long scheduleId) {
        return ResponseEntity.ok(scheduleService.getScheduleStatistics(scheduleId));
    }

    @PostMapping("/{scheduleId}/publish")
    public ResponseEntity<Schedule> publishSchedule(@PathVariable Long scheduleId) {
        return ResponseEntity.ok(scheduleService.publishSchedule(scheduleId));
    }
}
