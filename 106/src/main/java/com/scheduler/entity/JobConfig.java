package com.scheduler.entity;

import lombok.Data;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "job_config", uniqueConstraints = {
        @UniqueConstraint(columnNames = {"job_name", "job_group"})
})
public class JobConfig {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "job_name", nullable = false)
    private String jobName;

    @Column(name = "job_group", nullable = false)
    private String jobGroup;

    @Column(name = "retry_count", columnDefinition = "INT DEFAULT 0")
    private Integer retryCount = 0;

    @Column(name = "retry_interval", columnDefinition = "INT DEFAULT 30000")
    private Integer retryInterval = 30000;

    @Column(name = "timeout_seconds", columnDefinition = "INT DEFAULT 300")
    private Integer timeoutSeconds = 300;

    @Column(name = "depends_on", columnDefinition = "TEXT")
    private String dependsOn;

    @Column(name = "description")
    private String description;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @Column(name = "update_time")
    private LocalDateTime updateTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
        updateTime = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updateTime = LocalDateTime.now();
    }

}
