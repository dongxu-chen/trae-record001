package com.configcenter.server.entity;

import lombok.Data;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "config_audit_log")
public class ConfigAuditLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "application", nullable = false)
    private String application;

    @Column(name = "profile", nullable = false)
    private String profile;

    @Column(name = "label", nullable = false)
    private String label;

    @Column(name = "action", nullable = false)
    @Enumerated(EnumType.STRING)
    private ActionType action;

    @Column(name = "old_value", columnDefinition = "TEXT")
    private String oldValue;

    @Column(name = "new_value", columnDefinition = "TEXT")
    private String newValue;

    @Column(name = "version_before")
    private String versionBefore;

    @Column(name = "version_after")
    private String versionAfter;

    @Column(name = "operator", nullable = false)
    private String operator;

    @Column(name = "operator_ip")
    private String operatorIp;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "remark")
    private String remark;

    public enum ActionType {
        CREATE, UPDATE, PUBLISH, ROLLBACK, GRAY_RELEASE, GRAY_ROLLBACK, DELETE
    }

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}
