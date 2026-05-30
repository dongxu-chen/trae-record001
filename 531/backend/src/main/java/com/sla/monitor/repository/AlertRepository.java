package com.sla.monitor.repository;

import com.sla.monitor.model.Alert;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface AlertRepository extends JpaRepository<Alert, Long> {

    List<Alert> findByServiceNameOrderByCreatedAtDesc(String serviceName);

    List<Alert> findByResolvedFalseOrderByCreatedAtDesc();

    List<Alert> findByServiceNameAndResolvedFalseOrderByCreatedAtDesc(String serviceName);

    List<Alert> findByCreatedAtAfterOrderByCreatedAtDesc(LocalDateTime timestamp);

    List<Alert> findBySeverityAndResolvedFalseOrderByCreatedAtDesc(Alert.AlertSeverity severity);
}
