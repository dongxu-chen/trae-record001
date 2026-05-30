package com.health.task.repository;

import com.health.task.entity.HealthScorePrediction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface HealthScorePredictionRepository extends JpaRepository<HealthScorePrediction, Long> {

    List<HealthScorePrediction> findByTaskNameOrderByPredictionTimeDesc(String taskName);

    List<HealthScorePrediction> findByTaskNameAndPredictionTimeAfterOrderByPredictionTimeDesc(String taskName, LocalDateTime time);

    HealthScorePrediction findTopByTaskNameOrderByPredictionTimeDesc(String taskName);

    List<HealthScorePrediction> findByTaskNameAndTargetTimeAfterOrderByTargetTimeAsc(String taskName, LocalDateTime targetTime);
}
