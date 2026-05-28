package com.configcenter.server.entity;

import lombok.Data;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "config_version")
public class ConfigVersion {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "application", nullable = false)
    private String application;

    @Column(name = "profile", nullable = false)
    private String profile;

    @Column(name = "label", nullable = false)
    private String label;

    @Column(name = "version", nullable = false)
    private String version;

    @Column(name = "git_commit_id", length = 64)
    private String gitCommitId;

    @Column(name = "git_commit_message")
    private String gitCommitMessage;

    @Column(name = "config_content", columnDefinition = "TEXT")
    private String configContent;

    @Column(name = "change_summary")
    private String changeSummary;

    @Column(name = "operator", nullable = false)
    private String operator;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "status", nullable = false)
    @Enumerated(EnumType.STRING)
    private VersionStatus status;

    @Column(name = "rolled_back_from")
    private Long rolledBackFrom;

    public enum VersionStatus {
        DRAFT, PUBLISHED, ROLLED_BACK, ARCHIVED
    }

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        if (status == null) {
            status = VersionStatus.DRAFT;
        }
    }
}
