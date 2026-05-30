package com.taskflow.model;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "tf_task_lineage")
public class TaskLineage {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "data_product", nullable = false, length = 256)
    private String dataProduct;

    @Column(name = "source_workflow_id")
    private Long sourceWorkflowId;

    @Column(name = "source_task_key", length = 128)
    private String sourceTaskKey;

    @Column(name = "target_workflow_id", nullable = false)
    private Long targetWorkflowId;

    @Column(name = "target_task_key", length = 128)
    private String targetTaskKey;

    @Column(name = "lineage_type", nullable = false, length = 32)
    private String lineageType = "DATA";

    @Column(nullable = false)
    private Boolean enabled = true;

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
