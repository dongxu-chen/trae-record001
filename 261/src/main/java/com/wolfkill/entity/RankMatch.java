package com.wolfkill.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "rank_match")
public class RankMatch {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "match_id", nullable = false, unique = true)
    private Long matchId;

    @Column(name = "season_id", length = 64)
    private String seasonId;

    @Column(name = "game_mode", length = 32)
    private String gameMode;

    @Column(name = "room_id")
    private Long roomId;

    @Column(name = "status", length = 32)
    private String status;

    @Column(name = "team1_players", columnDefinition = "TEXT")
    private String team1Players;

    @Column(name = "team2_players", columnDefinition = "TEXT")
    private String team2Players;

    @Column(name = "team1_avg_elo")
    private Integer team1AvgElo;

    @Column(name = "team2_avg_elo")
    private Integer team2AvgElo;

    @Column(name = "winner_team")
    private Integer winnerTeam;

    @Column(name = "start_time")
    private LocalDateTime startTime;

    @Column(name = "end_time")
    private LocalDateTime endTime;

    @Column(name = "duration_seconds")
    private Integer durationSeconds;

    @Column(name = "total_days")
    private Integer totalDays;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
