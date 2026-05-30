package com.health.task.repository;

import com.health.task.entity.HealthScore;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface HealthScoreRepository extends JpaRepository<HealthScore, Long> {

    List<HealthScore> findByTaskNameOrderByCalculatedAtDesc(String taskName);

    Optional<HealthScore> findTopByTaskNameOrderByCalculatedAtDesc(String taskName);

    List<HealthScore> findByTaskNameAndCalculatedAtBetweenOrderByCalculatedAtAsc(
            String taskName, LocalDateTime start, LocalDateTime end);

    @Query("SELECT hs FROM HealthScore hs WHERE hs.calculatedAt = (SELECT MAX(hs2.calculatedAt) FROM HealthScore hs2 WHERE hs2.taskName = hs.taskName)")
    List<HealthScore> findLatestScoresForAllTasks();

    @Query("SELECT hs FROM HealthScore hs WHERE hs.overallScore < :threshold AND hs.calculatedAt = (SELECT MAX(hs2.calculatedAt) FROM HealthScore hs2 WHERE hs2.taskName = hs.taskName)")
    List<HealthScore> findUnhealthyTasks(@Param("threshold") int threshold);
}
