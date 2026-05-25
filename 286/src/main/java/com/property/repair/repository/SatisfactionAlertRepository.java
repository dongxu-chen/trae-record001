package com.property.repair.repository;

import com.property.repair.entity.SatisfactionAlert;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface SatisfactionAlertRepository extends JpaRepository<SatisfactionAlert, Long> {

    List<SatisfactionAlert> findByWorkerIdOrderByCreateTimeDesc(Long workerId);

    List<SatisfactionAlert> findByStatus(String status);

    List<SatisfactionAlert> findByWorkerIdAndCreateTimeAfter(Long workerId, LocalDateTime startTime);
}
