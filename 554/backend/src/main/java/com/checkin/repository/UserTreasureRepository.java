package com.checkin.repository;

import com.checkin.entity.UserTreasure;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface UserTreasureRepository extends JpaRepository<UserTreasure, Long> {
    List<UserTreasure> findByUserIdAndPeriod(Long userId, String period);
    Optional<UserTreasure> findByUserIdAndTreasureIdAndPeriod(Long userId, Long treasureId, String period);
}
