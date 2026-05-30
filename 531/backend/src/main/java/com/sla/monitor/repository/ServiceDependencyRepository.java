package com.sla.monitor.repository;

import com.sla.monitor.model.ServiceDependency;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface ServiceDependencyRepository extends JpaRepository<ServiceDependency, Long> {

    List<ServiceDependency> findByDownstreamServiceAndActiveTrue(String downstreamService);

    List<ServiceDependency> findByUpstreamServiceAndActiveTrue(String upstreamService);

    List<ServiceDependency> findByActiveTrue();

    @Query("SELECT d FROM ServiceDependency d WHERE d.downstreamService = :serviceName OR d.upstreamService = :serviceName")
    List<ServiceDependency> findAllDependenciesForService(@Param("serviceName") String serviceName);

    @Query("SELECT d FROM ServiceDependency d WHERE d.active = true AND (d.downstreamService = :serviceName OR d.upstreamService = :serviceName)")
    List<ServiceDependency> findAllActiveDependenciesForService(@Param("serviceName") String serviceName);

    boolean existsByDownstreamServiceAndUpstreamService(String downstreamService, String upstreamService);
}
