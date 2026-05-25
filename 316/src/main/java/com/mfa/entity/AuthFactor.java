package com.mfa.entity;

import com.mfa.enums.FactorType;
import jakarta.persistence.*;
import lombok.Data;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "auth_factors")
@EntityListeners(AuditingEntityListener.class)
public class AuthFactor {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private FactorType factorType;

    @Column(length = 50)
    private String name;

    @Column(length = 500)
    private String secret;

    @Column(length = 500)
    private String credentialId;

    @Column(length = 1000)
    private String publicKey;

    @Column
    private Long signCount;

    @Column(length = 500)
    private String aaguid;

    @Column(length = 100)
    private String deviceInfo;

    @Column(length = 100)
    private String deviceName;

    @Column(length = 100)
    private String deviceModel;

    @Column(length = 50)
    private String deviceOs;

    @Column(length = 100)
    private String deviceBrowser;

    @Column(length = 200)
    private String deviceFingerprint;

    @Column(length = 500)
    private String devicePublicKey;

    @Column
    private LocalDateTime lastSyncedAt;

    @Column(nullable = false)
    private boolean verified = false;

    @Column(nullable = false)
    private boolean enabled = true;

    @Column(nullable = false)
    private boolean revoked = false;

    @Column(length = 200)
    private String revokeReason;

    @Column
    private LocalDateTime revokedAt;

    @CreatedDate
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column(nullable = false)
    private LocalDateTime updatedAt;

    @Column
    private LocalDateTime lastUsedAt;
}
