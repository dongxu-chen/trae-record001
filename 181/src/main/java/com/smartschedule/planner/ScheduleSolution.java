package com.smartschedule.planner;

import com.smartschedule.entity.Employee;
import com.smartschedule.entity.Schedule;
import lombok.Data;
import org.optaplanner.core.api.domain.solution.PlanningEntityCollectionProperty;
import org.optaplanner.core.api.domain.solution.PlanningScore;
import org.optaplanner.core.api.domain.solution.PlanningSolution;
import org.optaplanner.core.api.domain.solution.ProblemFactCollectionProperty;
import org.optaplanner.core.api.domain.solution.ProblemFactProperty;
import org.optaplanner.core.api.domain.valuerange.ValueRangeProvider;
import org.optaplanner.core.api.score.buildin.hardmediumsoft.HardMediumSoftScore;

import java.util.List;

@Data
@PlanningSolution
public class ScheduleSolution {
    private Schedule schedule;

    @ProblemFactProperty
    private ConstraintWeights constraintWeights;

    @ProblemFactCollectionProperty
    @ValueRangeProvider
    private List<Employee> employees;

    @PlanningEntityCollectionProperty
    private List<PlannerShiftAssignment> assignments;

    @PlanningScore
    private HardMediumSoftScore score;

    public ScheduleSolution() {
    }

    public ScheduleSolution(Schedule schedule, ConstraintWeights constraintWeights,
                            List<Employee> employees, List<PlannerShiftAssignment> assignments) {
        this.schedule = schedule;
        this.constraintWeights = constraintWeights;
        this.employees = employees;
        this.assignments = assignments;
    }
}
