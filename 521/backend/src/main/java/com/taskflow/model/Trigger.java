package com.taskflow.model;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "tf_trigger")
public class Trigger {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "workflow_id", nullable = false)
    private Long workflowId;

    @Column(name = "trigger_type", nullable = false, length = 32)
    private String triggerType;

    @Column(name = "cron_expression", length = 128)
    private String cronExpression;

    @Column(name = "event_topic", length = 256)
    private String eventTopic;

    @Column(name = "event_filter", columnDefinition = "JSON")
    private String eventFilter;

    @Column(name = "webhook_path", length = 128, unique = true)
    private String webhookPath;

    @Column(name = "webhook_secret", length = 256)
    private String webhookSecret;

    @Column(nullable = false)
    private Boolean enabled = true;

    @Column(name = "last_trigger_time")
    private LocalDateTime lastTriggerTime;

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
