package com.checkin.repository;

import com.checkin.entity.CheckinConfig;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface CheckinConfigRepository extends JpaRepository<CheckinConfig, Long> {
    List<CheckinConfig> findByPeriodTypeAndEnabledTrueOrderByDayIndexAsc(String periodType);
    Optional<CheckinConfig> findByPeriodTypeAndDayIndexAndEnabledTrue(String periodType, Integer dayIndex);
}
