package com.health.task.repository;

import com.health.task.entity.SlaPrediction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface SlaPredictionRepository extends JpaRepository<SlaPrediction, Long> {

    List<SlaPrediction> findByTaskNameOrderByPredictionTimeDesc(String taskName);

    List<SlaPrediction> findByTaskNameAndPredictionTimeAfterOrderByPredictionTimeDesc(String taskName, LocalDateTime time);

    SlaPrediction findTopByTaskNameOrderByPredictionTimeDesc(String taskName);

    List<SlaPrediction> findBySlaStatusOrderByPredictionTimeDesc(String slaStatus);

    List<SlaPrediction> findByMonthStartAndMonthEnd(LocalDateTime monthStart, LocalDateTime monthEnd);
}
