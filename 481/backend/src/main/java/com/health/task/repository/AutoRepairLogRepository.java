package com.health.task.repository;

import com.health.task.entity.AutoRepairLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface AutoRepairLogRepository extends JpaRepository<AutoRepairLog, Long> {

    List<AutoRepairLog> findByTaskNameOrderByRepairTimeDesc(String taskName);

    List<AutoRepairLog> findByTaskNameAndRepairTimeAfterOrderByRepairTimeDesc(String taskName, LocalDateTime time);

    List<AutoRepairLog> findByStatusOrderByRepairTimeDesc(String status);

    List<AutoRepairLog> findByFailureTypeOrderByRepairTimeDesc(String failureType);

    long countByTaskNameAndStatus(String taskName, String status);
}
