package com.sla.monitor.repository;

import com.sla.monitor.model.CapacityPlan;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

public interface CapacityPlanRepository extends JpaRepository<CapacityPlan, Long> {

    List<CapacityPlan> findByServiceNameOrderByCreatedAtDesc(String serviceName);

    Optional<CapacityPlan> findFirstByServiceNameOrderByCreatedAtDesc(String serviceName);

    List<CapacityPlan> findByStatusOrderByCreatedAtDesc(CapacityPlan.CapacityStatus status);

    List<CapacityPlan> findByCreatedAtAfterOrderByCreatedAtDesc(LocalDateTime startTime);

    @Query("SELECT c FROM CapacityPlan c WHERE c.serviceName = :serviceName AND c.resourceType = :resourceType ORDER BY c.createdAt DESC")
    List<CapacityPlan> findByServiceNameAndResourceType(
            @Param("serviceName") String serviceName,
            @Param("resourceType") CapacityPlan.ResourceType resourceType);

    @Query("SELECT c FROM CapacityPlan c WHERE c.status IN :statuses ORDER BY c.createdAt DESC")
    List<CapacityPlan> findByStatusIn(@Param("statuses") List<CapacityPlan.CapacityStatus> statuses);
}
