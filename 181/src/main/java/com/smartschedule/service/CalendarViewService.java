package com.smartschedule.service;

import com.smartschedule.dto.CalendarCell;
import com.smartschedule.dto.CalendarEmployee;
import com.smartschedule.dto.CalendarViewData;
import com.smartschedule.entity.Employee;
import com.smartschedule.entity.Schedule;
import com.smartschedule.entity.ShiftAssignment;
import com.smartschedule.repository.ScheduleRepository;
import com.smartschedule.repository.ShiftAssignmentRepository;
import jakarta.persistence.EntityNotFoundException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class CalendarViewService {

    @Autowired
    private ScheduleRepository scheduleRepository;

    @Autowired
    private ShiftAssignmentRepository assignmentRepository;

    public CalendarViewData getCalendarView(Long scheduleId) {
        Schedule schedule = scheduleRepository.findById(scheduleId)
                .orElseThrow(() -> new EntityNotFoundException("Schedule not found"));

        List<ShiftAssignment> assignments = assignmentRepository.findByScheduleId(scheduleId);

        List<LocalDate> dates = generateDateRange(schedule.getStartDate(), schedule.getEndDate());

        Map<Employee, List<ShiftAssignment>> employeeAssignments = assignments.stream()
                .filter(a -> a.getEmployee() != null)
                .collect(Collectors.groupingBy(ShiftAssignment::getEmployee));

        List<CalendarEmployee> calendarEmployees = new ArrayList<>();
        Map<String, CalendarCell> cells = new HashMap<>();

        for (Map.Entry<Employee, List<ShiftAssignment>> entry : employeeAssignments.entrySet()) {
            Employee employee = entry.getKey();
            List<ShiftAssignment> empAssignments = entry.getValue();

            int totalHours = empAssignments.stream()
                    .mapToInt(a -> a.getShiftRequirement().getShiftType().getDurationHours())
                    .sum();

            CalendarEmployee calendarEmployee = new CalendarEmployee();
            calendarEmployee.setId(employee.getId());
            calendarEmployee.setName(employee.getName());
            calendarEmployee.setEmployeeNo(employee.getEmployeeNo());
            calendarEmployee.setTotalHours(totalHours);
            calendarEmployee.setTotalShifts(empAssignments.size());
            calendarEmployees.add(calendarEmployee);

            for (ShiftAssignment assignment : empAssignments) {
                String cellKey = employee.getId() + "_" + assignment.getShiftRequirement().getDate();

                CalendarCell cell = new CalendarCell();
                cell.setAssignmentId(assignment.getId());
                cell.setShiftRequirementId(assignment.getShiftRequirement().getId());
                cell.setShiftTypeId(assignment.getShiftRequirement().getShiftType().getId());
                cell.setShiftTypeName(assignment.getShiftRequirement().getShiftType().getName());
                cell.setShiftTypeCode(assignment.getShiftRequirement().getShiftType().getCode());
                cell.setStartTime(assignment.getShiftRequirement().getShiftType().getStartTime());
                cell.setEndTime(assignment.getShiftRequirement().getShiftType().getEndTime());
                cell.setColor(assignment.getShiftRequirement().getShiftType().getColor());
                cell.setIsLocked(assignment.getIsLocked());
                cell.setIsConflict(assignment.getIsConflict());
                cell.setConflictMessage(assignment.getConflictMessage());

                String shiftTypeCode = assignment.getShiftRequirement().getShiftType().getCode();
                cell.setIsPreferred(employee.getPreferredShiftTypes() != null
                        && employee.getPreferredShiftTypes().contains(shiftTypeCode));
                cell.setIsUnwanted(employee.getUnwantedShiftTypes() != null
                        && employee.getUnwantedShiftTypes().contains(shiftTypeCode));

                cells.put(cellKey, cell);
            }
        }

        CalendarViewData viewData = new CalendarViewData();
        viewData.setScheduleId(schedule.getId());
        viewData.setScheduleName(schedule.getName());
        viewData.setStartDate(schedule.getStartDate());
        viewData.setEndDate(schedule.getEndDate());
        viewData.setDates(dates);
        viewData.setEmployees(calendarEmployees);
        viewData.setCells(cells);

        return viewData;
    }

    public CalendarCell validateAssignmentChange(Long assignmentId, Long newEmployeeId) {
        ShiftAssignment assignment = assignmentRepository.findById(assignmentId)
                .orElseThrow(() -> new EntityNotFoundException("Assignment not found"));

        if (Boolean.TRUE.equals(assignment.getIsLocked())) {
            throw new IllegalStateException("Cannot modify locked assignment");
        }

        CalendarCell cell = new CalendarCell();
        cell.setAssignmentId(assignment.getId());

        if (newEmployeeId != null) {
            List<ShiftAssignment> employeeAssignments = assignmentRepository
                    .findByScheduleIdAndEmployeeId(assignment.getSchedule().getId(), newEmployeeId);

            Set<String> conflicts = detectConflicts(assignment, employeeAssignments, newEmployeeId);

            cell.setIsConflict(!conflicts.isEmpty());
            cell.setConflictMessage(String.join(";", conflicts));
        } else {
            cell.setIsConflict(false);
            cell.setConflictMessage(null);
        }

        return cell;
    }

    private Set<String> detectConflicts(ShiftAssignment currentAssignment,
                                        List<ShiftAssignment> employeeAssignments,
                                        Long newEmployeeId) {
        Set<String> conflicts = new LinkedHashSet<>();
        var currentRequirement = currentAssignment.getShiftRequirement();

        for (ShiftAssignment other : employeeAssignments) {
            if (other.getId().equals(currentAssignment.getId())) continue;
            if (other.getEmployee() == null) continue;
            if (!other.getEmployee().getId().equals(newEmployeeId)) continue;

            var otherRequirement = other.getShiftRequirement();

            if (otherRequirement.getDate().equals(currentRequirement.getDate())) {
                if (isTimeOverlapping(currentRequirement, otherRequirement)) {
                    conflicts.add("时间重叠: " + otherRequirement.getShiftType().getName());
                }
            }
        }

        return conflicts;
    }

    private boolean isTimeOverlapping(com.smartschedule.entity.ShiftRequirement r1,
                                      com.smartschedule.entity.ShiftRequirement r2) {
        return r1.getShiftType().getStartTime().isBefore(r2.getShiftType().getEndTime())
                && r2.getShiftType().getStartTime().isBefore(r1.getShiftType().getEndTime());
    }

    private List<LocalDate> generateDateRange(LocalDate start, LocalDate end) {
        List<LocalDate> dates = new ArrayList<>();
        LocalDate current = start;
        while (!current.isAfter(end)) {
            dates.add(current);
            current = current.plusDays(1);
        }
        return dates;
    }
}
