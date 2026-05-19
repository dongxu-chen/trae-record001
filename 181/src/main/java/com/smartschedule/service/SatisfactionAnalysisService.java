package com.smartschedule.service;

import com.smartschedule.dto.EmployeeSatisfaction;
import com.smartschedule.dto.ScheduleSatisfactionAnalysis;
import com.smartschedule.entity.Employee;
import com.smartschedule.entity.Schedule;
import com.smartschedule.entity.ShiftAssignment;
import com.smartschedule.repository.ScheduleRepository;
import com.smartschedule.repository.ShiftAssignmentRepository;
import jakarta.persistence.EntityNotFoundException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class SatisfactionAnalysisService {

    @Autowired
    private ShiftAssignmentRepository assignmentRepository;

    @Autowired
    private ScheduleRepository scheduleRepository;

    public ScheduleSatisfactionAnalysis analyzeSchedule(Long scheduleId) {
        Schedule schedule = scheduleRepository.findById(scheduleId)
                .orElseThrow(() -> new EntityNotFoundException("Schedule not found"));

        List<ShiftAssignment> assignments = assignmentRepository.findByScheduleId(scheduleId);

        List<EmployeeSatisfaction> employeeSatisfactions = calculateEmployeeSatisfactions(assignments);

        double preferenceSatisfactionRate = calculatePreferenceSatisfactionRate(employeeSatisfactions);
        double workloadFairnessScore = calculateWorkloadFairnessScore(employeeSatisfactions);
        double conflictRate = calculateConflictRate(assignments);

        int totalAssignments = assignments.size();
        int satisfiedAssignments = countSatisfiedAssignments(assignments);
        int conflictingAssignments = (int) assignments.stream()
                .filter(a -> Boolean.TRUE.equals(a.getIsConflict()))
                .count();

        double overallScore = calculateOverallScore(preferenceSatisfactionRate, workloadFairnessScore, conflictRate);

        Map<String, Object> fairnessMetrics = calculateFairnessMetrics(employeeSatisfactions);

        ScheduleSatisfactionAnalysis analysis = new ScheduleSatisfactionAnalysis();
        analysis.setOverallSatisfactionScore(overallScore);
        analysis.setPreferenceSatisfactionRate(preferenceSatisfactionRate);
        analysis.setWorkloadFairnessScore(workloadFairnessScore);
        analysis.setConflictRate(conflictRate);
        analysis.setTotalAssignments(totalAssignments);
        analysis.setSatisfiedAssignments(satisfiedAssignments);
        analysis.setConflictingAssignments(conflictingAssignments);
        analysis.setEmployeeSatisfactions(employeeSatisfactions);
        analysis.setFairnessMetrics(fairnessMetrics);

        return analysis;
    }

    private List<EmployeeSatisfaction> calculateEmployeeSatisfactions(List<ShiftAssignment> assignments) {
        Map<Employee, List<ShiftAssignment>> employeeAssignments = assignments.stream()
                .filter(a -> a.getEmployee() != null)
                .collect(Collectors.groupingBy(ShiftAssignment::getEmployee));

        List<EmployeeSatisfaction> satisfactions = new ArrayList<>();

        for (Map.Entry<Employee, List<ShiftAssignment>> entry : employeeAssignments.entrySet()) {
            Employee employee = entry.getKey();
            List<ShiftAssignment> empAssignments = entry.getValue();

            int preferredShifts = 0;
            int unwantedShifts = 0;
            int totalHours = 0;
            int conflicts = 0;

            for (ShiftAssignment assignment : empAssignments) {
                String shiftTypeCode = assignment.getShiftRequirement().getShiftType().getCode();

                if (employee.getPreferredShiftTypes() != null
                        && employee.getPreferredShiftTypes().contains(shiftTypeCode)) {
                    preferredShifts++;
                }

                if (employee.getUnwantedShiftTypes() != null
                        && employee.getUnwantedShiftTypes().contains(shiftTypeCode)) {
                    unwantedShifts++;
                }

                totalHours += assignment.getShiftRequirement().getShiftType().getDurationHours();

                if (Boolean.TRUE.equals(assignment.getIsConflict())) {
                    conflicts++;
                }
            }

            int totalShifts = empAssignments.size();
            double preferenceSatisfaction = totalShifts > 0 ?
                    (double) (preferredShifts - unwantedShifts * 0.5) / totalShifts : 0;
            preferenceSatisfaction = Math.max(0, Math.min(1, preferenceSatisfaction));

            EmployeeSatisfaction satisfaction = new EmployeeSatisfaction();
            satisfaction.setEmployeeId(employee.getId());
            satisfaction.setEmployeeName(employee.getName());
            satisfaction.setTotalShifts(totalShifts);
            satisfaction.setPreferredShifts(preferredShifts);
            satisfaction.setUnwantedShifts(unwantedShifts);
            satisfaction.setTotalHours(totalHours);
            satisfaction.setPreferenceSatisfaction(preferenceSatisfaction);
            satisfaction.setConflictCount(conflicts);
            satisfaction.setSatisfactionScore(calculateEmployeeScore(preferenceSatisfaction, conflicts, totalShifts));

            satisfactions.add(satisfaction);
        }

        return satisfactions;
    }

    private double calculateEmployeeScore(double preferenceSatisfaction, int conflicts, int totalShifts) {
        double conflictPenalty = totalShifts > 0 ? (double) conflicts / totalShifts * 0.3 : 0;
        double score = preferenceSatisfaction * 0.7 - conflictPenalty;
        return Math.max(0, Math.min(1, score));
    }

    private double calculatePreferenceSatisfactionRate(List<EmployeeSatisfaction> satisfactions) {
        if (satisfactions.isEmpty()) return 0.0;
        return satisfactions.stream()
                .mapToDouble(EmployeeSatisfaction::getPreferenceSatisfaction)
                .average()
                .orElse(0.0);
    }

    private double calculateWorkloadFairnessScore(List<EmployeeSatisfaction> satisfactions) {
        if (satisfactions.isEmpty()) return 0.0;

        List<Integer> hours = satisfactions.stream()
                .map(EmployeeSatisfaction::getTotalHours)
                .toList();

        double mean = hours.stream().mapToInt(Integer::intValue).average().orElse(0);
        if (mean == 0) return 1.0;

        double variance = hours.stream()
                .mapToDouble(h -> Math.pow(h - mean, 2))
                .average()
                .orElse(0);

        double stdDev = Math.sqrt(variance);
        double coefficientOfVariation = stdDev / mean;

        return Math.max(0, 1 - coefficientOfVariation);
    }

    private double calculateConflictRate(List<ShiftAssignment> assignments) {
        if (assignments.isEmpty()) return 0.0;
        long conflictCount = assignments.stream()
                .filter(a -> Boolean.TRUE.equals(a.getIsConflict()))
                .count();
        return (double) conflictCount / assignments.size();
    }

    private int countSatisfiedAssignments(List<ShiftAssignment> assignments) {
        int count = 0;
        for (ShiftAssignment assignment : assignments) {
            if (assignment.getEmployee() == null) continue;
            if (Boolean.TRUE.equals(assignment.getIsConflict())) continue;

            Employee employee = assignment.getEmployee();
            String shiftTypeCode = assignment.getShiftRequirement().getShiftType().getCode();

            boolean isPreferred = employee.getPreferredShiftTypes() != null
                    && employee.getPreferredShiftTypes().contains(shiftTypeCode);
            boolean isUnwanted = employee.getUnwantedShiftTypes() != null
                    && employee.getUnwantedShiftTypes().contains(shiftTypeCode);

            if (isPreferred || (!isPreferred && !isUnwanted)) {
                count++;
            }
        }
        return count;
    }

    private double calculateOverallScore(double preferenceRate, double fairnessScore, double conflictRate) {
        double preferenceWeight = 0.4;
        double fairnessWeight = 0.35;
        double conflictWeight = 0.25;

        return preferenceRate * preferenceWeight
                + fairnessScore * fairnessWeight
                + (1 - conflictRate) * conflictWeight;
    }

    private Map<String, Object> calculateFairnessMetrics(List<EmployeeSatisfaction> satisfactions) {
        Map<String, Object> metrics = new HashMap<>();

        List<Integer> hours = satisfactions.stream()
                .map(EmployeeSatisfaction::getTotalHours)
                .sorted()
                .toList();

        if (!hours.isEmpty()) {
            double mean = hours.stream().mapToInt(Integer::intValue).average().orElse(0);
            double variance = hours.stream()
                    .mapToDouble(h -> Math.pow(h - mean, 2))
                    .average()
                    .orElse(0);
            double stdDev = Math.sqrt(variance);

            metrics.put("meanHours", mean);
            metrics.put("minHours", Collections.min(hours));
            metrics.put("maxHours", Collections.max(hours));
            metrics.put("stdDeviation", stdDev);
            metrics.put("range", Collections.max(hours) - Collections.min(hours));
            metrics.put("employeeCount", satisfactions.size());

            List<Map<String, Object>> employeeHours = new ArrayList<>();
            for (EmployeeSatisfaction es : satisfactions) {
                Map<String, Object> emp = new HashMap<>();
                emp.put("employeeId", es.getEmployeeId());
                emp.put("employeeName", es.getEmployeeName());
                emp.put("totalHours", es.getTotalHours());
                emp.put("deviationFromMean", es.getTotalHours() - mean);
                employeeHours.add(emp);
            }
            metrics.put("employeeHours", employeeHours);
        }

        return metrics;
    }
}
