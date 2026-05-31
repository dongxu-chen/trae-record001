package com.checkin.repository;

import com.checkin.entity.CheckinAnalysis;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface CheckinAnalysisRepository extends JpaRepository<CheckinAnalysis, Long> {
    Optional<CheckinAnalysis> findByPeriodTypeAndAnalysisDate(String periodType, LocalDate analysisDate);
    List<CheckinAnalysis> findByPeriodTypeAndAnalysisDateBetweenOrderByAnalysisDateAsc(
            String periodType, LocalDate startDate, LocalDate endDate);
    
    @Query("SELECT ca FROM CheckinAnalysis ca WHERE ca.periodType = :periodType " +
           "ORDER BY ca.analysisDate DESC LIMIT :limit")
    List<CheckinAnalysis> findLatestAnalysis(@Param("periodType") String periodType, 
                                             @Param("limit") Integer limit);
}
