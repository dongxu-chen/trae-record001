package com.schemaregistry.repository;

import com.schemaregistry.model.AuditLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {
    List<AuditLog> findBySubjectOrderByCreatedAtDesc(String subject);

    List<AuditLog> findBySubjectAndVersionOrderByCreatedAtDesc(String subject, Integer version);

    List<AuditLog> findByUsernameOrderByCreatedAtDesc(String username);

    List<AuditLog> findByActionOrderByCreatedAtDesc(AuditLog.AuditAction action);

    List<AuditLog> findByCreatedAtAfterOrderByCreatedAtDesc(LocalDateTime dateTime);

    @Query("SELECT a FROM AuditLog a WHERE a.subject = :subject AND a.createdAt BETWEEN :start AND :end ORDER BY a.createdAt DESC")
    List<AuditLog> findBySubjectAndDateRange(
            @Param("subject") String subject,
            @Param("start") LocalDateTime start,
            @Param("end") LocalDateTime end);
}
