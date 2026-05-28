package com.configcenter.server.repository;

import com.configcenter.server.entity.ConfigAuditLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface ConfigAuditLogRepository extends JpaRepository<ConfigAuditLog, Long> {

    List<ConfigAuditLog> findByApplicationOrderByCreatedAtDesc(String application);

    List<ConfigAuditLog> findByApplicationAndProfileAndLabelOrderByCreatedAtDesc(
            String application, String profile, String label);

    @Query("SELECT log FROM ConfigAuditLog log WHERE log.application = :application " +
            "AND log.createdAt BETWEEN :startTime AND :endTime ORDER BY log.createdAt DESC")
    List<ConfigAuditLog> findByApplicationAndTimeRange(
            @Param("application") String application,
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime);

    @Query("SELECT log FROM ConfigAuditLog log WHERE log.operator = :operator ORDER BY log.createdAt DESC")
    List<ConfigAuditLog> findByOperator(@Param("operator") String operator);

    List<ConfigAuditLog> findByActionOrderByCreatedAtDesc(ConfigAuditLog.ActionType action);
}
