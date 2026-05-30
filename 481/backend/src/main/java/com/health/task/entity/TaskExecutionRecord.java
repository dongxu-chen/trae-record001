package com.health.task.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "task_execution_record")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TaskExecutionRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String taskName;

    @Column(nullable = false)
    private String taskGroup;

    private String cronExpression;

    @Column(nullable = false)
    private LocalDateTime startTime;

    private LocalDateTime endTime;

    @Column(nullable = false)
    private Long durationMs;

    @Column(nullable = false)
    private Boolean success;

    private String errorMessage;

    private Double cpuUsagePercent;

    private Double memoryUsageMb;

    @Column(nullable = false)
    private LocalDateTime createdAt;
}
