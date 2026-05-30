package com.sla.monitor.repository;

import com.sla.monitor.model.ServiceInfo;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ServiceInfoRepository extends JpaRepository<ServiceInfo, Long> {

    Optional<ServiceInfo> findByServiceName(String serviceName);

    List<ServiceInfo> findByActiveTrue();

    boolean existsByServiceName(String serviceName);
}
