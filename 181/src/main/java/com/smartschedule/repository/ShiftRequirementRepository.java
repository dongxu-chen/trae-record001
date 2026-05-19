package com.smartschedule.repository;

import com.smartschedule.entity.ShiftRequirement;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ShiftRequirementRepository extends JpaRepository<ShiftRequirement, Long> {
    List<ShiftRequirement> findByScheduleId(Long scheduleId);
    void deleteByScheduleId(Long scheduleId);
}
