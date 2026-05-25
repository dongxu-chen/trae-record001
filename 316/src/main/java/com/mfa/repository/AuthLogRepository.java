package com.mfa.repository;

import com.mfa.entity.AuthLog;
import com.mfa.enums.AuthStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface AuthLogRepository extends JpaRepository<AuthLog, Long> {

    List<AuthLog> findByUserIdOrderByCreatedAtDesc(Long userId);

    Page<AuthLog> findByUserIdOrderByCreatedAtDesc(Long userId, Pageable pageable);

    List<AuthLog> findByUsernameOrderByCreatedAtDesc(String username);

    List<AuthLog> findBySessionIdOrderByCreatedAtAsc(String sessionId);

    List<AuthLog> findByIpAddressAndCreatedAtAfter(String ipAddress, LocalDateTime since);

    @Query("SELECT COUNT(a) FROM AuthLog a WHERE a.user.id = :userId AND a.status = :status AND a.createdAt >= :since")
    long countByUserIdAndStatusAndCreatedAtAfter(
            @Param("userId") Long userId,
            @Param("status") AuthStatus status,
            @Param("since") LocalDateTime since);

    @Query("SELECT COUNT(DISTINCT a.ipAddress) FROM AuthLog a WHERE a.user.id = :userId AND a.createdAt >= :since")
    long countDistinctIpAddressesByUserIdAndCreatedAtAfter(
            @Param("userId") Long userId,
            @Param("since") LocalDateTime since);

    Page<AuthLog> findAllByOrderByCreatedAtDesc(Pageable pageable);

    Page<AuthLog> findByStatusOrderByCreatedAtDesc(AuthStatus status, Pageable pageable);

    @Query("SELECT COUNT(a) FROM AuthLog a WHERE a.createdAt >= :start AND a.createdAt < :end")
    long countByCreatedAtBetween(@Param("start") LocalDateTime start, @Param("end") LocalDateTime end);

    @Query("SELECT COUNT(a) FROM AuthLog a WHERE a.status = :status AND a.createdAt >= :start AND a.createdAt < :end")
    long countByStatusAndCreatedAtBetween(
            @Param("status") AuthStatus status,
            @Param("start") LocalDateTime start,
            @Param("end") LocalDateTime end);

    @Query("SELECT COUNT(DISTINCT a.user.id) FROM AuthLog a WHERE a.createdAt >= :start AND a.createdAt < :end")
    long countDistinctUsersByCreatedAtBetween(@Param("start") LocalDateTime start, @Param("end") LocalDateTime end);

    @Query("SELECT a.factorType, a.status, COUNT(a) FROM AuthLog a " +
           "WHERE a.createdAt >= :start AND a.createdAt < :end " +
           "GROUP BY a.factorType, a.status")
    List<Object[]> countByFactorTypeAndStatusAndCreatedAtBetween(
            @Param("start") LocalDateTime start, @Param("end") LocalDateTime end);

    @Query("SELECT FUNCTION('DATE', a.createdAt), a.status, COUNT(a) FROM AuthLog a " +
           "WHERE a.createdAt >= :start AND a.createdAt < :end " +
           "GROUP BY FUNCTION('DATE', a.createdAt), a.status " +
           "ORDER BY FUNCTION('DATE', a.createdAt)")
    List<Object[]> countByDateAndStatusAndCreatedAtBetween(
            @Param("start") LocalDateTime start, @Param("end") LocalDateTime end);

    @Query("SELECT a.riskLevel, COUNT(a) FROM AuthLog a " +
           "WHERE a.createdAt >= :start AND a.createdAt < :end " +
           "GROUP BY a.riskLevel")
    List<Object[]> countByRiskLevelAndCreatedAtBetween(
            @Param("start") LocalDateTime start, @Param("end") LocalDateTime end);

    @Query("SELECT a.message, COUNT(a) FROM AuthLog a " +
           "WHERE a.status = 'FAILED' AND a.createdAt >= :start AND a.createdAt < :end " +
           "GROUP BY a.message ORDER BY COUNT(a) DESC")
    List<Object[]> countFailureReasonsByCreatedAtBetween(
            @Param("start") LocalDateTime start, @Param("end") LocalDateTime end);
}
