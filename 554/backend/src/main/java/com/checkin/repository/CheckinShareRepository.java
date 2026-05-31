package com.checkin.repository;

import com.checkin.entity.CheckinShare;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface CheckinShareRepository extends JpaRepository<CheckinShare, Long> {
    List<CheckinShare> findByUserIdOrderByCreateTimeDesc(Long userId);
    Optional<CheckinShare> findByUserIdAndShareDate(Long userId, LocalDate shareDate);
    List<CheckinShare> findByUserIdAndShareDateBetween(Long userId, LocalDate startDate, LocalDate endDate);
    
    @Query("SELECT COUNT(cs) FROM CheckinShare cs WHERE cs.userId = :userId AND cs.rewardClaimed = true")
    Integer countClaimedShares(@Param("userId") Long userId);
    
    @Query("SELECT SUM(cs.viewCount) FROM CheckinShare cs WHERE cs.userId = :userId")
    Long sumViewCount(@Param("userId") Long userId);
}
