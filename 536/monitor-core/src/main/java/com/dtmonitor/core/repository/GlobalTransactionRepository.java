package com.dtmonitor.core.repository;

import com.dtmonitor.core.enums.TransactionMode;
import com.dtmonitor.core.enums.TransactionStatus;
import com.dtmonitor.core.model.entity.GlobalTransaction;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface GlobalTransactionRepository extends JpaRepository<GlobalTransaction, String> {

    Page<GlobalTransaction> findByStatus(TransactionStatus status, Pageable pageable);

    Page<GlobalTransaction> findByMode(TransactionMode mode, Pageable pageable);

    Page<GlobalTransaction> findByApplicationId(String applicationId, Pageable pageable);

    Page<GlobalTransaction> findByModeAndStatus(TransactionMode mode, TransactionStatus status, Pageable pageable);

    List<GlobalTransaction> findByStatusAndBeginTimeBefore(TransactionStatus status, LocalDateTime time);

    @Query("SELECT t FROM GlobalTransaction t WHERE " +
           "(:mode IS NULL OR t.mode = :mode) AND " +
           "(:status IS NULL OR t.status = :status) AND " +
           "(:applicationId IS NULL OR t.applicationId = :applicationId) AND " +
           "(:trafficColor IS NULL OR t.trafficColor = :trafficColor) AND " +
           "(:businessType IS NULL OR t.businessType = :businessType) AND " +
           "(:startTime IS NULL OR t.beginTime >= :startTime) AND " +
           "(:endTime IS NULL OR t.beginTime <= :endTime)")
    Page<GlobalTransaction> search(
            @Param("mode") TransactionMode mode,
            @Param("status") TransactionStatus status,
            @Param("applicationId") String applicationId,
            @Param("trafficColor") String trafficColor,
            @Param("businessType") String businessType,
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime,
            Pageable pageable);

    Page<GlobalTransaction> findByTrafficColor(String trafficColor, Pageable pageable);

    Page<GlobalTransaction> findByBusinessType(String businessType, Pageable pageable);

    @Query("SELECT DISTINCT t.trafficColor FROM GlobalTransaction t WHERE t.trafficColor IS NOT NULL")
    List<String> findDistinctTrafficColors();

    @Query("SELECT DISTINCT t.businessType FROM GlobalTransaction t WHERE t.businessType IS NOT NULL")
    List<String> findDistinctBusinessTypes();

    long countByStatus(TransactionStatus status);

    long countByMode(TransactionMode mode);

    @Query("SELECT COUNT(t) FROM GlobalTransaction t WHERE t.beginTime >= :since")
    long countSince(@Param("since") LocalDateTime since);

    @Query("SELECT t.mode, COUNT(t) FROM GlobalTransaction t GROUP BY t.mode")
    List<Object[]> countByModeGroup();

    @Query("SELECT t.status, COUNT(t) FROM GlobalTransaction t GROUP BY t.status")
    List<Object[]> countByStatusGroup();
}
