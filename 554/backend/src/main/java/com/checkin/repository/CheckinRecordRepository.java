package com.checkin.repository;

import com.checkin.entity.CheckinRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface CheckinRecordRepository extends JpaRepository<CheckinRecord, Long> {
    List<CheckinRecord> findByUserIdAndPeriodTypeAndCheckinDateBetween(
            Long userId, String periodType, LocalDate startDate, LocalDate endDate);

    boolean existsByUserIdAndCheckinDateAndPeriodType(Long userId, LocalDate checkinDate, String periodType);

    CheckinRecord findByUserIdAndCheckinDateAndPeriodType(Long userId, LocalDate checkinDate, String periodType);

    @Query("SELECT COUNT(c) FROM CheckinRecord c WHERE c.userId = :userId AND c.periodType = :periodType " +
           "AND c.checkinDate BETWEEN :startDate AND :endDate")
    Integer countCheckinDays(@Param("userId") Long userId, @Param("periodType") String periodType,
                             @Param("startDate") LocalDate startDate, @Param("endDate") LocalDate endDate);
}
