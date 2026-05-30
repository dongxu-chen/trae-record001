package com.sla.monitor.repository;

import com.sla.monitor.model.RootCauseAnalysis;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface RootCauseAnalysisRepository extends JpaRepository<RootCauseAnalysis, Long> {

    List<RootCauseAnalysis> findByServiceNameOrderByTimestampDesc(String serviceName);

    List<RootCauseAnalysis> findByServiceNameAndTimestampAfterOrderByTimestampDesc(
            String serviceName, LocalDateTime timestamp);
}
