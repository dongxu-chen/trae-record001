package com.mfa.entity;

import com.mfa.enums.AuthStatus;
import com.mfa.enums.FactorType;
import jakarta.persistence.*;
import lombok.Data;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "auth_logs", indexes = {
    @Index(name = "idx_user_id", columnList = "user_id"),
    @Index(name = "idx_session_id", columnList = "sessionId"),
    @Index(name = "idx_created_at", columnList = "createdAt"),
    @Index(name = "idx_status", columnList = "status")
})
@EntityListeners(AuditingEntityListener.class)
public class AuthLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 64)
    private String sessionId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id")
    private User user;

    @Column(length = 50)
    private String username;

    @Enumerated(EnumType.STRING)
    @Column(length = 30)
    private FactorType factorType;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private AuthStatus status;

    @Column(length = 500)
    private String message;

    @Column(length = 50)
    private String ipAddress;

    @Column(length = 200)
    private String userAgent;

    @Column(length = 100)
    private String location;

    @Column
    private String deviceFingerprint;

    @Column
    private Integer riskScore;

    @Column(length = 20)
    private String riskLevel;

    @Column(length = 500)
    private String riskFactors;

    @Column
    private boolean stepUpRequired;

    @Column(length = 1000)
    private String additionalInfo;

    @CreatedDate
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;
}
