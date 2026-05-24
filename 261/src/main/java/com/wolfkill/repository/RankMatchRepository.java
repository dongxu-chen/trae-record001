package com.wolfkill.repository;

import com.wolfkill.entity.RankMatch;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface RankMatchRepository extends JpaRepository<RankMatch, Long> {
    Optional<RankMatch> findByMatchId(Long matchId);
}
