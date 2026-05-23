package com.shortlink.repository;

import com.shortlink.entity.AccessLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface AccessLogRepository extends JpaRepository<AccessLog, Long> {

    @Query("SELECT COUNT(DISTINCT a.ip) FROM AccessLog a WHERE a.shortCode = :shortCode AND a.accessTime BETWEEN :start AND :end")
    Long countDistinctIpByShortCodeAndAccessTimeBetween(String shortCode, LocalDateTime start, LocalDateTime end);

    @Query("SELECT a.deviceType, COUNT(a) FROM AccessLog a WHERE a.shortCode = :shortCode GROUP BY a.deviceType")
    List<Object[]> countByDeviceType(String shortCode);

    @Query("SELECT a.browser, COUNT(a) FROM AccessLog a WHERE a.shortCode = :shortCode GROUP BY a.browser")
    List<Object[]> countByBrowser(String shortCode);

    @Query("SELECT a.country, COUNT(a) FROM AccessLog a WHERE a.shortCode = :shortCode AND a.country IS NOT NULL GROUP BY a.country")
    List<Object[]> countByCountry(String shortCode);

    @Query("SELECT a.province, COUNT(a) FROM AccessLog a WHERE a.shortCode = :shortCode AND a.province IS NOT NULL GROUP BY a.province")
    List<Object[]> countByProvince(String shortCode);

    @Query("SELECT DATE(a.accessTime), COUNT(a) FROM AccessLog a WHERE a.shortCode = :shortCode AND a.accessTime BETWEEN :start AND :end GROUP BY DATE(a.accessTime)")
    List<Object[]> countByDate(String shortCode, LocalDateTime start, LocalDateTime end);

    @Query("SELECT FUNCTION('DATE_FORMAT', a.accessTime, '%Y-%m-%d %H:00:00'), COUNT(a) " +
           "FROM AccessLog a WHERE a.shortCode = :shortCode AND a.accessTime BETWEEN :start AND :end " +
           "GROUP BY FUNCTION('DATE_FORMAT', a.accessTime, '%Y-%m-%d %H:00:00') " +
           "ORDER BY FUNCTION('DATE_FORMAT', a.accessTime, '%Y-%m-%d %H:00:00')")
    List<Object[]> countByHour(String shortCode, LocalDateTime start, LocalDateTime end);

    @Query("SELECT a FROM AccessLog a WHERE a.shortCode = :shortCode AND a.accessTime BETWEEN :start AND :end ORDER BY a.accessTime")
    List<AccessLog> findByShortCodeAndAccessTimeBetween(String shortCode, LocalDateTime start, LocalDateTime end);
}
