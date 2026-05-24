package com.wolfkill.entity;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "voice_room")
public class VoiceRoom {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "room_id", nullable = false)
    private Long roomId;

    @Column(name = "voice_room_id", unique = true, length = 64)
    private String voiceRoomId;

    @Column(name = "room_type", length = 32)
    private String roomType;

    @Column(name = "room_token", length = 128)
    private String roomToken;

    @Column(name = "voice_server", length = 128)
    private String voiceServer;

    @Column(name = "voice_port")
    private Integer voicePort;

    @Column(name = "is_active")
    private Boolean active = true;

    @Column(name = "max_users")
    private Integer maxUsers = 12;

    @Column(name = "current_users")
    private Integer currentUsers = 0;

    @Column(name = "allowed_user_ids", columnDefinition = "TEXT")
    private String allowedUserIds;

    @Column(name = "expire_time")
    private LocalDateTime expireTime;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
