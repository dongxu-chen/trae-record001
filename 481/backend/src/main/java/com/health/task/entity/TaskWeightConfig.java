package com.health.task.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "task_weight_config")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TaskWeightConfig {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String taskName;

    private String taskGroup;

    @Column(nullable = false)
    private String importanceLevel;

    @Column(nullable = false)
    private Double durationWeight;

    @Column(nullable = false)
    private Double successRateWeight;

    @Column(nullable = false)
    private Double frequencyWeight;

    @Column(nullable = false)
    private Double resourceWeight;

    private String description;
}
