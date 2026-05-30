package com.sla.monitor.repository;

import com.sla.monitor.model.SlaMetrics;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface SlaMetricsRepository extends JpaRepository<SlaMetrics, Long> {

    List<SlaMetrics> findByServiceNameAndTimestampAfterOrderByTimestampAsc(
            String serviceName, LocalDateTime timestamp);

    List<SlaMetrics> findByServiceNameAndWindowTypeAndTimestampAfterOrderByTimestampAsc(
            String serviceName, String windowType, LocalDateTime timestamp);

    @Query("SELECT m FROM SlaMetrics m WHERE m.serviceName = :serviceName " +
           "AND m.timestamp >= :startTime AND m.timestamp <= :endTime " +
           "ORDER BY m.timestamp ASC")
    List<SlaMetrics> findByServiceNameAndTimeRange(
            @Param("serviceName") String serviceName,
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime);

    @Query("SELECT DISTINCT m.serviceName FROM SlaMetrics m")
    List<String> findDistinctServiceNames();

    SlaMetrics findFirstByServiceNameOrderByTimestampDesc(String serviceName);
}
