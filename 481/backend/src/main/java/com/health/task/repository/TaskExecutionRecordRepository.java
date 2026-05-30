package com.health.task.repository;

import com.health.task.entity.TaskExecutionRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface TaskExecutionRecordRepository extends JpaRepository<TaskExecutionRecord, Long> {

    List<TaskExecutionRecord> findByTaskNameAndCreatedAtBetweenOrderByCreatedAtDesc(
            String taskName, LocalDateTime start, LocalDateTime end);

    List<TaskExecutionRecord> findByCreatedAtBetweenOrderByCreatedAtDesc(
            LocalDateTime start, LocalDateTime end);

    @Query("SELECT DISTINCT r.taskName FROM TaskExecutionRecord r")
    List<String> findAllTaskNames();

    @Query("SELECT COUNT(r) FROM TaskExecutionRecord r WHERE r.taskName = :taskName AND r.success = true AND r.createdAt BETWEEN :start AND :end")
    long countSuccessByTaskNameAndTimeRange(@Param("taskName") String taskName,
                                             @Param("start") LocalDateTime start,
                                             @Param("end") LocalDateTime end);

    @Query("SELECT COUNT(r) FROM TaskExecutionRecord r WHERE r.taskName = :taskName AND r.createdAt BETWEEN :start AND :end")
    long countByTaskNameAndTimeRange(@Param("taskName") String taskName,
                                      @Param("start") LocalDateTime start,
                                      @Param("end") LocalDateTime end);

    @Query("SELECT AVG(r.durationMs) FROM TaskExecutionRecord r WHERE r.taskName = :taskName AND r.createdAt BETWEEN :start AND :end")
    Double avgDurationByTaskNameAndTimeRange(@Param("taskName") String taskName,
                                              @Param("start") LocalDateTime start,
                                              @Param("end") LocalDateTime end);

    @Query("SELECT AVG(r.cpuUsagePercent) FROM TaskExecutionRecord r WHERE r.taskName = :taskName AND r.createdAt BETWEEN :start AND :end")
    Double avgCpuByTaskNameAndTimeRange(@Param("taskName") String taskName,
                                         @Param("start") LocalDateTime start,
                                         @Param("end") LocalDateTime end);

    @Query("SELECT AVG(r.memoryUsageMb) FROM TaskExecutionRecord r WHERE r.taskName = :taskName AND r.createdAt BETWEEN :start AND :end")
    Double avgMemoryByTaskNameAndTimeRange(@Param("taskName") String taskName,
                                            @Param("start") LocalDateTime start,
                                            @Param("end") LocalDateTime end);

    @Query("SELECT MAX(r.durationMs) FROM TaskExecutionRecord r WHERE r.taskName = :taskName AND r.createdAt BETWEEN :start AND :end")
    Long maxDurationByTaskNameAndTimeRange(@Param("taskName") String taskName,
                                            @Param("start") LocalDateTime start,
                                            @Param("end") LocalDateTime end);
}
