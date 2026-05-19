package com.smartschedule.service;

import com.smartschedule.config.ConstraintWeightConfig;
import com.smartschedule.entity.*;
import com.smartschedule.planner.ConstraintWeights;
import com.smartschedule.planner.PlannerShiftAssignment;
import com.smartschedule.planner.ScheduleSolution;
import com.smartschedule.repository.*;
import jakarta.persistence.EntityNotFoundException;
import org.optaplanner.core.api.solver.Solver;
import org.optaplanner.core.api.solver.SolverFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Service
public class ScheduleService {

    @Autowired
    private ScheduleRepository scheduleRepository;

    @Autowired
    private EmployeeRepository employeeRepository;

    @Autowired
    private ShiftRequirementRepository requirementRepository;

    @Autowired
    private ShiftAssignmentRepository assignmentRepository;

    @Autowired
    private SolverFactory<ScheduleSolution> solverFactory;

    @Autowired
    private ConstraintWeightConfig weightConfig;

    @Autowired
    private PushNotificationService pushNotificationService;

    private final Map<Long, ScheduleSolution> solvingCache = new ConcurrentHashMap<>();

    private ConstraintWeights buildConstraintWeights() {
        return new ConstraintWeights(
                weightConfig.getRequiredSkillMatch(),
                weightConfig.getNoOverlappingShifts(),
                weightConfig.getMaxDailyHours(),
                weightConfig.getMaxWeeklyHours(),
                weightConfig.getMinWeeklyHours(),
                weightConfig.getUnavailableDays(),
                weightConfig.getMaxConsecutiveDays(),
                weightConfig.getMaxConsecutiveNightShifts(),
                weightConfig.getUnwantedShiftTypes(),
                weightConfig.getPreferredShiftTypes(),
                weightConfig.getBalancedWorkload(),
                weightConfig.getShiftRotation(),
                weightConfig.getAssignEveryShift(),
                weightConfig.getMaxConsecutiveNightShiftsLimit()
        );
    }

    @Transactional
    public Schedule createSchedule(Schedule schedule) {
        schedule.setStatus(Schedule.ScheduleStatus.DRAFT);
        return scheduleRepository.save(schedule);
    }

    public Schedule getSchedule(Long id) {
        return scheduleRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("Schedule not found with id: " + id));
    }

    public List<Schedule> getAllSchedules() {
        return scheduleRepository.findAll();
    }

    @Transactional
    public void deleteSchedule(Long id) {
        assignmentRepository.deleteByScheduleId(id);
        requirementRepository.deleteByScheduleId(id);
        scheduleRepository.deleteById(id);
    }

    @Transactional
    public ShiftRequirement addShiftRequirement(Long scheduleId, ShiftRequirement requirement) {
        Schedule schedule = getSchedule(scheduleId);
        requirement.setSchedule(schedule);
        return requirementRepository.save(requirement);
    }

    public List<ShiftRequirement> getShiftRequirements(Long scheduleId) {
        return requirementRepository.findByScheduleId(scheduleId);
    }

    @Transactional
    public ScheduleSolution generateSchedule(Long scheduleId) {
        Schedule schedule = getSchedule(scheduleId);
        schedule.setStatus(Schedule.ScheduleStatus.SOLVING);
        scheduleRepository.save(schedule);

        List<Employee> employees = employeeRepository.findByIsActiveTrue();
        List<ShiftRequirement> requirements = requirementRepository.findByScheduleId(scheduleId);
        ConstraintWeights constraintWeights = buildConstraintWeights();

        List<PlannerShiftAssignment> plannerAssignments = new ArrayList<>();
        long assignmentId = 1;

        for (ShiftRequirement requirement : requirements) {
            for (int i = 0; i < requirement.getRequiredCount(); i++) {
                PlannerShiftAssignment plannerAssignment = new PlannerShiftAssignment(
                        assignmentId++,
                        requirement,
                        false
                );
                plannerAssignments.add(plannerAssignment);
            }
        }

        ScheduleSolution problem = new ScheduleSolution(schedule, constraintWeights, employees, plannerAssignments);
        solvingCache.put(scheduleId, problem);

        Solver<ScheduleSolution> solver = solverFactory.buildSolver();
        solver.addEventListener(event -> {
            ScheduleSolution newBestSolution = event.getNewBestSolution();
            solvingCache.put(scheduleId, newBestSolution);
        });

        ScheduleSolution solution = solver.solve(problem);

        schedule.setStatus(Schedule.ScheduleStatus.SOLVED);
        schedule.setSolvedAt(LocalDateTime.now());
        scheduleRepository.save(schedule);

        saveAssignments(scheduleId, solution);
        solvingCache.remove(scheduleId);

        return solution;
    }

    @Transactional
    public void saveAssignments(Long scheduleId, ScheduleSolution solution) {
        List<ShiftAssignment> existingAssignments = assignmentRepository.findByScheduleId(scheduleId);
        Map<Long, ShiftAssignment> existingMap = existingAssignments.stream()
                .collect(Collectors.toMap(a -> a.getShiftRequirement().getId() + "-" + a.getIndexInShift(), a -> a));

        assignmentRepository.deleteByScheduleId(scheduleId);
        Schedule schedule = getSchedule(scheduleId);

        int index = 0;
        for (PlannerShiftAssignment plannerAssignment : solution.getAssignments()) {
            ShiftAssignment assignment = new ShiftAssignment();
            assignment.setSchedule(schedule);
            assignment.setShiftRequirement(plannerAssignment.getShiftRequirement());
            assignment.setEmployee(plannerAssignment.getEmployee());
            assignment.setIndexInShift(index++);
            assignment.setIsLocked(plannerAssignment.getIsLocked() != null ? plannerAssignment.getIsLocked() : false);
            assignment.setIsConflict(false);
            assignmentRepository.save(assignment);
        }
    }

    public List<ShiftAssignment> getAssignments(Long scheduleId) {
        return assignmentRepository.findByScheduleId(scheduleId);
    }

    @Transactional
    public ShiftAssignment updateAssignment(Long assignmentId, Long employeeId) {
        ShiftAssignment assignment = assignmentRepository.findById(assignmentId)
                .orElseThrow(() -> new EntityNotFoundException("Assignment not found"));

        if (Boolean.TRUE.equals(assignment.getIsLocked())) {
            throw new IllegalStateException("Cannot modify locked assignment");
        }

        ShiftAssignment oldAssignment = new ShiftAssignment();
        oldAssignment.setEmployee(assignment.getEmployee());
        oldAssignment.setShiftRequirement(assignment.getShiftRequirement());

        if (employeeId != null) {
            Employee employee = employeeRepository.findById(employeeId)
                    .orElseThrow(() -> new EntityNotFoundException("Employee not found"));
            assignment.setEmployee(employee);
        } else {
            assignment.setEmployee(null);
        }

        detectConflicts(assignment);
        ShiftAssignment savedAssignment = assignmentRepository.save(assignment);

        if (savedAssignment.getEmployee() != null
                && (oldAssignment.getEmployee() == null
                || !oldAssignment.getEmployee().getId().equals(savedAssignment.getEmployee().getId()))) {
            pushNotificationService.createShiftChangeNotification(oldAssignment, savedAssignment);
            pushNotificationService.sendPendingNotifications();
        }

        return savedAssignment;
    }

    @Transactional
    public Schedule publishSchedule(Long scheduleId) {
        Schedule schedule = getSchedule(scheduleId);

        if (schedule.getStatus() == Schedule.ScheduleStatus.PUBLISHED) {
            throw new IllegalStateException("Schedule is already published");
        }

        List<ShiftAssignment> assignments = assignmentRepository.findByScheduleId(scheduleId);
        long unassignedCount = assignments.stream()
                .filter(a -> a.getEmployee() == null)
                .count();
        if (unassignedCount > 0) {
            throw new IllegalStateException("Cannot publish schedule with unassigned shifts: " + unassignedCount);
        }

        long conflictCount = assignments.stream()
                .filter(a -> Boolean.TRUE.equals(a.getIsConflict()))
                .count();
        if (conflictCount > 0) {
            throw new IllegalStateException("Cannot publish schedule with conflicts: " + conflictCount);
        }

        schedule.setStatus(Schedule.ScheduleStatus.PUBLISHED);
        schedule.setUpdatedAt(LocalDateTime.now());
        Schedule savedSchedule = scheduleRepository.save(schedule);

        pushNotificationService.createSchedulePublishedNotifications(savedSchedule);
        pushNotificationService.sendPendingNotifications();

        return savedSchedule;
    }

    @Transactional
    public ShiftAssignment lockAssignment(Long assignmentId, boolean locked) {
        ShiftAssignment assignment = assignmentRepository.findById(assignmentId)
                .orElseThrow(() -> new EntityNotFoundException("Assignment not found"));
        assignment.setIsLocked(locked);
        return assignmentRepository.save(assignment);
    }

    @Transactional
    public void lockAllAssignmentsBeforeDate(Long scheduleId, LocalDate date) {
        List<ShiftAssignment> assignments = assignmentRepository.findByScheduleId(scheduleId);
        for (ShiftAssignment assignment : assignments) {
            if (assignment.getShiftRequirement().getDate().isBefore(date)) {
                assignment.setIsLocked(true);
            }
        }
        assignmentRepository.saveAll(assignments);
    }

    private void detectConflicts(ShiftAssignment assignment) {
        if (assignment.getEmployee() == null) {
            assignment.setIsConflict(false);
            assignment.setConflictMessage(null);
            return;
        }

        List<ShiftAssignment> employeeAssignments = assignmentRepository
                .findByScheduleIdAndEmployeeId(
                        assignment.getSchedule().getId(),
                        assignment.getEmployee().getId());

        ShiftRequirement currentRequirement = assignment.getShiftRequirement();
        StringBuilder conflicts = new StringBuilder();

        for (ShiftAssignment other : employeeAssignments) {
            if (other.getId().equals(assignment.getId())) continue;
            if (other.getEmployee() == null) continue;

            ShiftRequirement otherRequirement = other.getShiftRequirement();

            if (otherRequirement.getDate().equals(currentRequirement.getDate())) {
                if (isTimeOverlapping(currentRequirement, otherRequirement)) {
                    conflicts.append("时间重叠;");
                }
            }
        }

        assignment.setIsConflict(conflicts.length() > 0);
        assignment.setConflictMessage(conflicts.length() > 0 ? conflicts.toString() : null);
    }

    private boolean isTimeOverlapping(ShiftRequirement r1, ShiftRequirement r2) {
        return r1.getShiftType().getStartTime().isBefore(r2.getShiftType().getEndTime())
                && r2.getShiftType().getStartTime().isBefore(r1.getShiftType().getEndTime());
    }

    @Transactional
    public ScheduleSolution recalculateSchedule(Long scheduleId) {
        Schedule schedule = getSchedule(scheduleId);
        List<ShiftAssignment> existingAssignments = assignmentRepository.findByScheduleId(scheduleId);

        ScheduleSolution solution = rebuildSolutionFromAssignments(schedule, existingAssignments);

        Solver<ScheduleSolution> solver = solverFactory.buildSolver();
        ScheduleSolution newSolution = solver.solve(solution);

        saveAssignmentsPreservingLocks(scheduleId, newSolution, existingAssignments);

        return newSolution;
    }

    @Transactional
    public ScheduleSolution incrementalRecalculate(Long scheduleId) {
        Schedule schedule = getSchedule(scheduleId);
        List<ShiftAssignment> existingAssignments = assignmentRepository.findByScheduleId(scheduleId);

        ScheduleSolution solution = rebuildSolutionFromAssignments(schedule, existingAssignments);

        Solver<ScheduleSolution> solver = solverFactory.buildSolver();
        ScheduleSolution newSolution = solver.solve(solution);

        saveAssignmentsPreservingLocks(scheduleId, newSolution, existingAssignments);

        return newSolution;
    }

    private void saveAssignmentsPreservingLocks(Long scheduleId, ScheduleSolution solution,
                                                List<ShiftAssignment> existingAssignments) {
        assignmentRepository.deleteByScheduleId(scheduleId);
        Schedule schedule = getSchedule(scheduleId);

        for (int i = 0; i < solution.getAssignments().size(); i++) {
            PlannerShiftAssignment plannerAssignment = solution.getAssignments().get(i);
            ShiftAssignment assignment = new ShiftAssignment();
            assignment.setSchedule(schedule);
            assignment.setShiftRequirement(plannerAssignment.getShiftRequirement());
            assignment.setEmployee(plannerAssignment.getEmployee());
            assignment.setIndexInShift(i);
            assignment.setIsLocked(plannerAssignment.getIsLocked() != null && plannerAssignment.getIsLocked());
            assignment.setIsConflict(false);
            assignmentRepository.save(assignment);
        }
    }

    private ScheduleSolution rebuildSolutionFromAssignments(Schedule schedule, List<ShiftAssignment> assignments) {
        List<Employee> employees = employeeRepository.findByIsActiveTrue();
        ConstraintWeights constraintWeights = buildConstraintWeights();
        List<PlannerShiftAssignment> plannerAssignments = new ArrayList<>();

        for (int i = 0; i < assignments.size(); i++) {
            ShiftAssignment assignment = assignments.get(i);
            PlannerShiftAssignment plannerAssignment = new PlannerShiftAssignment(
                    (long) (i + 1),
                    assignment.getShiftRequirement(),
                    assignment.getEmployee(),
                    assignment.getIsLocked()
            );
            plannerAssignments.add(plannerAssignment);
        }

        return new ScheduleSolution(schedule, constraintWeights, employees, plannerAssignments);
    }

    public Map<String, Object> getScheduleStatistics(Long scheduleId) {
        List<ShiftAssignment> assignments = assignmentRepository.findByScheduleId(scheduleId);

        Map<Employee, Long> employeeShiftCounts = assignments.stream()
                .filter(a -> a.getEmployee() != null)
                .collect(Collectors.groupingBy(ShiftAssignment::getEmployee, Collectors.counting()));

        long unassignedCount = assignments.stream()
                .filter(a -> a.getEmployee() == null)
                .count();

        long conflictCount = assignments.stream()
                .filter(a -> Boolean.TRUE.equals(a.getIsConflict()))
                .count();

        long lockedCount = assignments.stream()
                .filter(a -> Boolean.TRUE.equals(a.getIsLocked()))
                .count();

        return Map.of(
                "totalAssignments", assignments.size(),
                "assignedCount", assignments.size() - unassignedCount,
                "unassignedCount", unassignedCount,
                "conflictCount", conflictCount,
                "lockedCount", lockedCount,
                "employeeWorkload", employeeShiftCounts
        );
    }
}
