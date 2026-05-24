package com.wolfkill.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "rank_season")
public class RankSeason {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "season_id", nullable = false, unique = true, length = 64)
    private String seasonId;

    @Column(name = "season_name", nullable = false, length = 64)
    private String seasonName;

    @Column(name = "start_time", nullable = false)
    private LocalDateTime startTime;

    @Column(name = "end_time", nullable = false)
    private LocalDateTime endTime;

    @Column(name = "is_active")
    private Boolean active = false;

    @Column(name = "total_players")
    private Integer totalPlayers = 0;

    @Column(name = "total_games")
    private Integer totalGames = 0;

    @Column(name = "base_elo")
    private Integer baseElo = 1200;

    @Column(name = "k_factor")
    private Integer kFactor = 32;

    @Column(name = "rank_thresholds", columnDefinition = "TEXT")
    private String rankThresholds;

    @Column(name = "description", columnDefinition = "TEXT")
    private String description;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
