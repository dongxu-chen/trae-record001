package com.wolfkill.repository;

import com.wolfkill.entity.PlayerStats;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface PlayerStatsRepository extends JpaRepository<PlayerStats, Long> {
    Optional<PlayerStats> findByPlayerIdAndSeasonId(Long playerId, String seasonId);
    Optional<PlayerStats> findByPlayerId(Long playerId);

    @Query("SELECT p FROM PlayerStats p WHERE p.seasonId = ?1 ORDER BY p.elo DESC")
    Page<PlayerStats> findBySeasonIdOrderByEloDesc(String seasonId, Pageable pageable);

    @Query("SELECT COUNT(p) FROM PlayerStats p WHERE p.seasonId = ?1 AND p.elo > ?2")
    Long countPlayersWithHigherElo(String seasonId, Integer elo);

    @Query("SELECT p FROM PlayerStats p WHERE p.seasonId = ?1 AND p.totalGames > 0 ORDER BY p.elo DESC LIMIT ?2")
    List<PlayerStats> findTopPlayers(String seasonId, int limit);
}
