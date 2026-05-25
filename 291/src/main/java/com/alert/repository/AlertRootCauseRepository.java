package com.alert.repository;

import com.alert.entity.AlertRootCause;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface AlertRootCauseRepository extends JpaRepository<AlertRootCause, Long> {

    Optional<AlertRootCause> findByRootCauseId(String rootCauseId);

    List<AlertRootCause> findByStatus(String status);

    @Query("SELECT r FROM AlertRootCause r WHERE r.createTime BETWEEN ?1 AND ?2 ORDER BY r.createTime DESC")
    List<AlertRootCause> findByTimeRange(LocalDateTime startTime, LocalDateTime endTime);

    @Query("SELECT r FROM AlertRootCause r WHERE r.status = 'CONFIRMED' ORDER BY r.confidenceScore DESC")
    List<AlertRootCause> findTopConfirmedRootCauses();
}
