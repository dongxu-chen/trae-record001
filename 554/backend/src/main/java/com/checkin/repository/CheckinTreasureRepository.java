package com.checkin.repository;

import com.checkin.entity.CheckinTreasure;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface CheckinTreasureRepository extends JpaRepository<CheckinTreasure, Long> {
    List<CheckinTreasure> findByPeriodTypeAndEnabledTrueOrderByTotalDaysAsc(String periodType);
}
