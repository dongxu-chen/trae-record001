package com.wolfkill.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "game_room")
public class GameRoom {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 128)
    private String roomName;

    @Column(nullable = false)
    private Integer maxPlayers;

    @Column(nullable = false)
    private Integer currentPlayers = 0;

    @Column(length = 64)
    private String password;

    @Column(name = "host_id", nullable = false)
    private Long hostId;

    @Column(name = "game_phase")
    private Integer gamePhase = 0;

    @Column(name = "day_number")
    private Integer dayNumber = 0;

    @Column(name = "is_active")
    private Boolean active = true;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
