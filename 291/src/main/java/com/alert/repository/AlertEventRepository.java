package com.alert.repository;

import com.alert.entity.AlertEvent;
import com.alert.enums.AlertStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface AlertEventRepository extends JpaRepository<AlertEvent, Long>, JpaSpecificationExecutor<AlertEvent> {

    Optional<AlertEvent> findByAlertId(String alertId);

    List<AlertEvent> findByStatus(AlertStatus status);

    List<AlertEvent> findByStatusIn(List<AlertStatus> statuses);

    List<AlertEvent> findByAggregationKey(String aggregationKey);

    List<AlertEvent> findByParentAlertId(String parentAlertId);

    @Query("SELECT a FROM AlertEvent a WHERE a.status IN ?1 AND a.nextUpgradeTime <= ?2")
    List<AlertEvent> findAlertsToEscalate(List<AlertStatus> statuses, LocalDateTime now);

    @Query("SELECT COUNT(a) FROM AlertEvent a WHERE a.status = ?1")
    long countByStatus(AlertStatus status);
}
