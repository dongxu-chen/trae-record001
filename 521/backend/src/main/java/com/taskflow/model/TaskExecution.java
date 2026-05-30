package com.taskflow.model;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "tf_task_execution")
public class TaskExecution {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "workflow_execution_id", nullable = false)
    private Long workflowExecutionId;

    @Column(name = "task_id", nullable = false)
    private Long taskId;

    @Column(name = "task_key", nullable = false, length = 128)
    private String taskKey;

    @Column(nullable = false, length = 32)
    private String status = "PENDING";

    @Column(nullable = false)
    private Integer attempt = 1;

    @Column(name = "worker_node", length = 128)
    private String workerNode;

    @Column(name = "started_at")
    private LocalDateTime startedAt;

    @Column(name = "finished_at")
    private LocalDateTime finishedAt;

    @Column(name = "duration_ms")
    private Long durationMs;

    @Column(name = "log_text", columnDefinition = "TEXT")
    private String logText;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

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
