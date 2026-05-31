package com.checkin.repository;

import com.checkin.entity.CheckinStats;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface CheckinStatsRepository extends JpaRepository<CheckinStats, Long> {
    Optional<CheckinStats> findByUserIdAndPeriodTypeAndPeriod(Long userId, String periodType, String period);
}
