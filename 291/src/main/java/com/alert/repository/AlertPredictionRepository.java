package com.alert.repository;

import com.alert.entity.AlertPrediction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface AlertPredictionRepository extends JpaRepository<AlertPrediction, Long> {

    Optional<AlertPrediction> findByPredictionId(String predictionId);

    List<AlertPrediction> findByStatus(String status);

    @Query("SELECT p FROM AlertPrediction p WHERE p.predictedTime BETWEEN ?1 AND ?2 ORDER BY p.probability DESC")
    List<AlertPrediction> findByPredictedTimeRange(LocalDateTime startTime, LocalDateTime endTime);

    @Query("SELECT p FROM AlertPrediction p WHERE p.status = 'PREDICTED' AND p.predictedTime > ?1 ORDER BY p.probability DESC")
    List<AlertPrediction> findActivePredictions(LocalDateTime now);
}
