package com.smartschedule.planner;

import com.smartschedule.entity.Employee;
import com.smartschedule.entity.ShiftRequirement;
import org.optaplanner.core.api.score.buildin.hardmediumsoft.HardMediumSoftScore;
import org.optaplanner.core.api.score.stream.Constraint;
import org.optaplanner.core.api.score.stream.ConstraintFactory;
import org.optaplanner.core.api.score.stream.ConstraintProvider;
import org.optaplanner.core.api.score.stream.Joiners;

import java.time.LocalDate;
import java.util.List;

public class ScheduleConstraintProvider implements ConstraintProvider {

    @Override
    public Constraint[] defineConstraints(ConstraintFactory factory) {
        return new Constraint[]{
                requiredSkillMatch(factory),
                noOverlappingShifts(factory),
                maxDailyHours(factory),
                maxWeeklyHours(factory),
                minWeeklyHours(factory),
                unavailableDays(factory),
                maxConsecutiveDays(factory),
                maxConsecutiveNightShifts(factory),
                unwantedShiftTypes(factory),
                preferredShiftTypes(factory),
                balancedWorkload(factory),
                shiftRotation(factory),
                assignEveryShift(factory)
        };
    }

    private Constraint requiredSkillMatch(ConstraintFactory factory) {
        return factory.forEach(PlannerShiftAssignment.class)
                .filter(assignment -> assignment.getEmployee() != null
                        && assignment.getShiftRequirement().getRequiredSkill() != null
                        && assignment.getEmployee().getSkills().stream()
                        .noneMatch(skill -> skill.getId().equals(
                                assignment.getShiftRequirement().getRequiredSkill().getId())))
                .penalize(HardMediumSoftScore.ONE_HARD,
                        assignment -> assignment.getShiftRequirement().getSchedule() != null ? 1 : 0)
                .asConstraint("技能不匹配");
    }

    private Constraint noOverlappingShifts(ConstraintFactory factory) {
        return factory.forEach(PlannerShiftAssignment.class)
                .filter(assignment -> assignment.getEmployee() != null)
                .join(PlannerShiftAssignment.class,
                        Joiners.equal(assignment -> assignment.getEmployee().getId()),
                        Joiners.equal(assignment -> assignment.getShiftRequirement().getDate()),
                        Joiners.lessThan(PlannerShiftAssignment::getId))
                .filter((a1, a2) -> isOverlapping(a1.getShiftRequirement(), a2.getShiftRequirement()))
                .penalize(HardMediumSoftScore.ONE_HARD, (a1, a2) -> 100)
                .asConstraint("同一时间班次重叠");
    }

    private boolean isOverlapping(ShiftRequirement r1, ShiftRequirement r2) {
        return r1.getShiftType().getStartTime().isBefore(r2.getShiftType().getEndTime())
                && r2.getShiftType().getStartTime().isBefore(r1.getShiftType().getEndTime());
    }

    private Constraint maxDailyHours(ConstraintFactory factory) {
        return factory.forEach(PlannerShiftAssignment.class)
                .filter(assignment -> assignment.getEmployee() != null)
                .groupBy(
                        assignment -> assignment.getEmployee().getId(),
                        assignment -> assignment.getShiftRequirement().getDate(),
                        org.optaplanner.core.api.score.stream.ConstraintCollectors.sum(
                                assignment -> assignment.getShiftRequirement().getShiftType().getDurationHours()))
                .filter((employeeId, date, totalHours) -> totalHours > 8)
                .penalize(HardMediumSoftScore.ONE_HARD,
                        (employeeId, date, totalHours) -> (totalHours - 8) * 10)
                .asConstraint("每日工时超限");
    }

    private Constraint maxWeeklyHours(ConstraintFactory factory) {
        return factory.forEach(PlannerShiftAssignment.class)
                .filter(assignment -> assignment.getEmployee() != null)
                .groupBy(
                        assignment -> assignment.getEmployee().getId(),
                        assignment -> getWeekNumber(assignment.getShiftRequirement().getDate()),
                        org.optaplanner.core.api.score.stream.ConstraintCollectors.sum(
                                assignment -> assignment.getShiftRequirement().getShiftType().getDurationHours()))
                .filter((employeeId, week, totalHours) -> totalHours > 40)
                .penalize(HardMediumSoftScore.ONE_HARD,
                        (employeeId, week, totalHours) -> (totalHours - 40) * 5)
                .asConstraint("每周工时超限");
    }

    private int getWeekNumber(LocalDate date) {
        return date.getYear() * 52 + date.getDayOfYear() / 7;
    }

    private Constraint minWeeklyHours(ConstraintFactory factory) {
        return factory.forEach(PlannerShiftAssignment.class)
                .filter(assignment -> assignment.getEmployee() != null)
                .groupBy(
                        assignment -> assignment.getEmployee().getId(),
                        assignment -> getWeekNumber(assignment.getShiftRequirement().getDate()),
                        org.optaplanner.core.api.score.stream.ConstraintCollectors.sum(
                                assignment -> assignment.getShiftRequirement().getShiftType().getDurationHours()))
                .filter((employeeId, week, totalHours) -> totalHours < 20)
                .penalize(HardMediumSoftScore.ONE_MEDIUM,
                        (employeeId, week, totalHours) -> (20 - totalHours) * 3)
                .asConstraint("每周工时不足");
    }

    private Constraint unavailableDays(ConstraintFactory factory) {
        return factory.forEach(PlannerShiftAssignment.class)
                .filter(assignment -> assignment.getEmployee() != null
                        && assignment.getEmployee().getUnavailableDays() != null
                        && assignment.getEmployee().getUnavailableDays().contains(
                                assignment.getShiftRequirement().getDate().getDayOfWeek()))
                .penalize(HardMediumSoftScore.ONE_HARD, 200)
                .asConstraint("不可用日期排班");
    }

    private Constraint maxConsecutiveDays(ConstraintFactory factory) {
        return factory.forEach(Employee.class)
                .join(PlannerShiftAssignment.class,
                        Joiners.equal(Employee::getId, assignment -> assignment.getEmployee().getId()))
                .groupBy((employee, assignment) -> employee.getId(),
                        org.optaplanner.core.api.score.stream.ConstraintCollectors.collect(
                                assignment -> assignment.getShiftRequirement().getDate(),
                                org.optaplanner.core.api.score.stream.ConstraintCollectors.toList()))
                .filter((employeeId, dates) -> hasExceededConsecutiveDays(dates, 5))
                .penalize(HardMediumSoftScore.ONE_MEDIUM, 50)
                .asConstraint("连续工作天数超限");
    }

    private boolean hasExceededConsecutiveDays(List<LocalDate> dates, int maxConsecutive) {
        if (dates.size() <= maxConsecutive) {
            return false;
        }
        List<LocalDate> sortedDates = dates.stream().sorted().toList();
        int consecutive = 1;
        for (int i = 1; i < sortedDates.size(); i++) {
            if (sortedDates.get(i - 1).plusDays(1).equals(sortedDates.get(i))) {
                consecutive++;
                if (consecutive > maxConsecutive) {
                    return true;
                }
            } else {
                consecutive = 1;
            }
        }
        return false;
    }

    private Constraint maxConsecutiveNightShifts(ConstraintFactory factory) {
        return factory.forEach(Employee.class)
                .join(PlannerShiftAssignment.class,
                        Joiners.equal(Employee::getId, assignment -> assignment.getEmployee().getId()),
                        Joiners.filtering((employee, assignment) ->
                                "NIGHT".equals(assignment.getShiftRequirement().getShiftType().getCode())))
                .groupBy((employee, assignment) -> employee.getId(),
                        org.optaplanner.core.api.score.stream.ConstraintCollectors.collect(
                                assignment -> assignment.getShiftRequirement().getDate(),
                                org.optaplanner.core.api.score.stream.ConstraintCollectors.toList()))
                .filter((employeeId, dates) -> hasExceededConsecutiveNightShifts(dates, 2))
                .penalize(HardMediumSoftScore.ONE_HARD, 500)
                .asConstraint("连续夜班天数超限");
    }

    private boolean hasExceededConsecutiveNightShifts(List<LocalDate> dates, int maxConsecutive) {
        if (dates.size() <= maxConsecutive) {
            return false;
        }
        List<LocalDate> sortedDates = dates.stream().sorted().toList();
        int consecutive = 1;
        for (int i = 1; i < sortedDates.size(); i++) {
            if (sortedDates.get(i - 1).plusDays(1).equals(sortedDates.get(i))) {
                consecutive++;
                if (consecutive > maxConsecutive) {
                    return true;
                }
            } else {
                consecutive = 1;
            }
        }
        return false;
    }

    private Constraint unwantedShiftTypes(ConstraintFactory factory) {
        return factory.forEach(PlannerShiftAssignment.class)
                .filter(assignment -> assignment.getEmployee() != null
                        && assignment.getEmployee().getUnwantedShiftTypes() != null
                        && assignment.getEmployee().getUnwantedShiftTypes().contains(
                                assignment.getShiftRequirement().getShiftType().getCode()))
                .penalize(HardMediumSoftScore.ONE_SOFT, 10)
                .asConstraint("非偏好班次类型");
    }

    private Constraint preferredShiftTypes(ConstraintFactory factory) {
        return factory.forEach(PlannerShiftAssignment.class)
                .filter(assignment -> assignment.getEmployee() != null
                        && assignment.getEmployee().getPreferredShiftTypes() != null
                        && assignment.getEmployee().getPreferredShiftTypes().contains(
                                assignment.getShiftRequirement().getShiftType().getCode()))
                .reward(HardMediumSoftScore.ONE_SOFT, 5)
                .asConstraint("偏好班次类型");
    }

    private Constraint balancedWorkload(ConstraintFactory factory) {
        return factory.forEach(PlannerShiftAssignment.class)
                .filter(assignment -> assignment.getEmployee() != null)
                .groupBy(
                        assignment -> assignment.getEmployee().getId(),
                        org.optaplanner.core.api.score.stream.ConstraintCollectors.count())
                .groupBy(
                        org.optaplanner.core.api.score.stream.ConstraintCollectors.averagingInt(
                                (employeeId, count) -> count),
                        org.optaplanner.core.api.score.stream.ConstraintCollectors.toList(
                                (employeeId, count) -> count))
                .penalize(HardMediumSoftScore.ONE_SOFT,
                        (average, counts) -> {
                            int sumSquaredDeviations = 0;
                            for (int count : counts) {
                                int deviation = (int) (count - average);
                                sumSquaredDeviations += deviation * deviation;
                            }
                            return sumSquaredDeviations * 2;
                        })
                .asConstraint("工作负载均衡");
    }

    private Constraint shiftRotation(ConstraintFactory factory) {
        return factory.forEach(Employee.class)
                .join(PlannerShiftAssignment.class,
                        Joiners.equal(Employee::getId, assignment -> assignment.getEmployee().getId()))
                .groupBy((employee, assignment) -> employee.getId(),
                        org.optaplanner.core.api.score.stream.ConstraintCollectors.collect(
                                assignment -> assignment.getShiftRequirement().getDate() + "-"
                                        + assignment.getShiftRequirement().getShiftType().getCode(),
                                org.optaplanner.core.api.score.stream.ConstraintCollectors.toList()))
                .filter((employeeId, assignments) -> hasNoRotation(assignments))
                .penalize(HardMediumSoftScore.ONE_SOFT, 15)
                .asConstraint("班次轮换");
    }

    private boolean hasNoRotation(List<String> assignments) {
        if (assignments.size() < 3) {
            return false;
        }
        long uniqueShiftTypes = assignments.stream()
                .map(s -> s.split("-")[1])
                .distinct()
                .count();
        return uniqueShiftTypes == 1;
    }

    private Constraint assignEveryShift(ConstraintFactory factory) {
        return factory.forEach(PlannerShiftAssignment.class)
                .filter(assignment -> assignment.getEmployee() == null)
                .penalize(HardMediumSoftScore.ONE_MEDIUM, 100)
                .asConstraint("班次未分配");
    }
}
