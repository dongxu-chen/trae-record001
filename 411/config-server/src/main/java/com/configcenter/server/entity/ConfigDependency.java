package com.configcenter.server.entity;

import lombok.Data;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "config_dependency")
public class ConfigDependency {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "source_application", nullable = false)
    private String sourceApplication;

    @Column(name = "source_profile", nullable = false)
    private String sourceProfile;

    @Column(name = "source_label", nullable = false)
    private String sourceLabel;

    @Column(name = "source_config_key", nullable = false)
    private String sourceConfigKey;

    @Column(name = "target_application", nullable = false)
    private String targetApplication;

    @Column(name = "target_profile", nullable = false)
    private String targetProfile;

    @Column(name = "target_label", nullable = false)
    private String targetLabel;

    @Column(name = "target_config_key", nullable = false)
    private String targetConfigKey;

    @Column(name = "dependency_type", nullable = false)
    @Enumerated(EnumType.STRING)
    private DependencyType dependencyType;

    @Column(name = "description")
    private String description;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public enum DependencyType {
        REQUIRED, OPTIONAL, DERIVED, INHERITED
    }

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
