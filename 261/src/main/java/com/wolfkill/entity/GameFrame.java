package com.wolfkill.entity;

import jakarta.persistence.*;
import lombok.Data;

@Data
@Entity
@Table(name = "game_frame")
public class GameFrame {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "record_id", nullable = false)
    private Long recordId;

    @Column(name = "frame_index", nullable = false)
    private Integer frameIndex;

    @Column(nullable = false)
    private Long timestamp;

    @Column(name = "day_number")
    private Integer dayNumber;

    @Column(name = "game_phase")
    private Integer gamePhase;

    @Column(name = "event_type", length = 64)
    private String eventType;

    @Column(name = "event_data", columnDefinition = "TEXT")
    private String eventData;

    @Column(name = "player_states", columnDefinition = "LONGTEXT")
    private String playerStates;
}
