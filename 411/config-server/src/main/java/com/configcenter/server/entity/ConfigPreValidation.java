package com.configcenter.server.entity;

import lombok.Data;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "config_pre_validation")
public class ConfigPreValidation {

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

    @Column(name = "test_instance_url", nullable = false)
    private String testInstanceUrl;

    @Column(name = "status", nullable = false)
    @Enumerated(EnumType.STRING)
    private ValidationStatus status;

    @Column(name = "validation_result", columnDefinition = "TEXT")
    private String validationResult;

    @Column(name = "start_time", nullable = false)
    private LocalDateTime startTime;

    @Column(name = "end_time")
    private LocalDateTime endTime;

    @Column(name = "created_by", nullable = false)
    private String createdBy;

    public enum ValidationStatus {
        PENDING, RUNNING, PASSED, FAILED, TIMEOUT, CANCELLED
    }

    @PrePersist
    protected void onCreate() {
        startTime = LocalDateTime.now();
        if (status == null) {
            status = ValidationStatus.PENDING;
        }
    }
}
