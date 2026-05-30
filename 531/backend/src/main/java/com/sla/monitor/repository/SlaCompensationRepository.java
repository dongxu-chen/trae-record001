package com.sla.monitor.repository;

import com.sla.monitor.model.SlaCompensation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;

public interface SlaCompensationRepository extends JpaRepository<SlaCompensation, Long> {

    List<SlaCompensation> findByServiceNameOrderByCreatedAtDesc(String serviceName);

    List<SlaCompensation> findByApprovedFalseOrderByCreatedAtDesc();

    List<SlaCompensation> findByCreatedAtAfterOrderByCreatedAtDesc(LocalDateTime startTime);

    @Query("SELECT c FROM SlaCompensation c WHERE c.serviceName = :serviceName AND c.createdAt >= :startTime ORDER BY c.createdAt DESC")
    List<SlaCompensation> findByServiceNameAndCreatedAtAfter(
            @Param("serviceName") String serviceName,
            @Param("startTime") LocalDateTime startTime);

    @Query("SELECT c FROM SlaCompensation c WHERE c.violationSeverity = :severity ORDER BY c.createdAt DESC")
    List<SlaCompensation> findByViolationSeverity(@Param("severity") SlaCompensation.ViolationSeverity severity);
}
