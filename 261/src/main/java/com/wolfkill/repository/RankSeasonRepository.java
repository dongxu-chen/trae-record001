package com.wolfkill.repository;

import com.wolfkill.entity.RankSeason;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface RankSeasonRepository extends JpaRepository<RankSeason, Long> {
    Optional<RankSeason> findBySeasonId(String seasonId);
    Optional<RankSeason> findByActiveTrue();
}
