package com.smartschedule.planner;

import com.smartschedule.entity.Employee;
import com.smartschedule.entity.ShiftRequirement;
import lombok.Data;
import org.optaplanner.core.api.domain.entity.PlanningEntity;
import org.optaplanner.core.api.domain.lookup.PlanningId;
import org.optaplanner.core.api.domain.pin.PlanningPin;
import org.optaplanner.core.api.domain.variable.PlanningVariable;

@Data
@PlanningEntity
public class PlannerShiftAssignment {
    @PlanningId
    private Long id;

    private ShiftRequirement shiftRequirement;

    @PlanningVariable(nullable = true)
    private Employee employee;

    @PlanningPin
    private Boolean isLocked;

    public PlannerShiftAssignment() {
    }

    public PlannerShiftAssignment(Long id, ShiftRequirement shiftRequirement, Boolean isLocked) {
        this.id = id;
        this.shiftRequirement = shiftRequirement;
        this.isLocked = isLocked;
    }

    public PlannerShiftAssignment(Long id, ShiftRequirement shiftRequirement, Employee employee, Boolean isLocked) {
        this(id, shiftRequirement, isLocked);
        this.employee = employee;
    }
}
