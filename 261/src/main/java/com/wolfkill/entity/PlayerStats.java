package com.wolfkill.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "player_stats")
public class PlayerStats {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "player_id", nullable = false, unique = true)
    private Long playerId;

    @Column(name = "season_id", length = 64)
    private String seasonId;

    @Column(nullable = false)
    private Integer elo = 1200;

    @Column(name = "rank_level")
    private Integer rankLevel = 0;

    @Column(name = "rank_name", length = 32)
    private String rankName = "青铜";

    @Column(nullable = false)
    private Integer wins = 0;

    @Column(nullable = false)
    private Integer losses = 0;

    @Column(name = "win_streak")
    private Integer winStreak = 0;

    @Column(name = "max_win_streak")
    private Integer maxWinStreak = 0;

    @Column(name = "total_games")
    private Integer totalGames = 0;

    @Column(name = "wolf_wins")
    private Integer wolfWins = 0;

    @Column(name = "wolf_games")
    private Integer wolfGames = 0;

    @Column(name = "villager_wins")
    private Integer villagerWins = 0;

    @Column(name = "villager_games")
    private Integer villagerGames = 0;

    @Column(name = "seer_wins")
    private Integer seerWins = 0;

    @Column(name = "seer_games")
    private Integer seerGames = 0;

    @Column(name = "witch_wins")
    private Integer witchWins = 0;

    @Column(name = "witch_games")
    private Integer witchGames = 0;

    @Column(name = "hunter_wins")
    private Integer hunterWins = 0;

    @Column(name = "hunter_games")
    private Integer hunterGames = 0;

    @Column(name = "guard_wins")
    private Integer guardWins = 0;

    @Column(name = "guard_games")
    private Integer guardGames = 0;

    @Column(name = "total_kills")
    private Integer totalKills = 0;

    @Column(name = "total_saves")
    private Integer totalSaves = 0;

    @Column(name = "total_checks")
    private Integer totalChecks = 0;

    @Column(name = "correct_checks")
    private Integer correctChecks = 0;

    @Column(name = "correct_votes")
    private Integer correctVotes = 0;

    @Column(name = "total_votes")
    private Integer totalVotes = 0;

    @Column(name = "play_time_seconds")
    private Long playTimeSeconds = 0L;

    @Column(name = "last_game_time")
    private LocalDateTime lastGameTime;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
