package com.configcenter.server.entity;

import lombok.Data;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "config_snapshot")
public class ConfigSnapshot {

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

    @Column(name = "config_content", columnDefinition = "TEXT", nullable = false)
    private String configContent;

    @Column(name = "snapshot_time", nullable = false)
    private LocalDateTime snapshotTime;

    @Column(name = "description")
    private String description;

    @Column(name = "created_by", nullable = false)
    private String createdBy;

    @Column(name = "git_commit_id", length = 64)
    private String gitCommitId;

    @PrePersist
    protected void onCreate() {
        if (snapshotTime == null) {
            snapshotTime = LocalDateTime.now();
        }
    }
}
