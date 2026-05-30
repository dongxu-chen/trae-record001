package com.health.task.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "optimization_script")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OptimizationScript {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String issueCategory;

    @Column(nullable = false)
    private String scriptType;

    @Column(nullable = false)
    private String scriptName;

    @Column(nullable = false, length = 4000)
    private String scriptContent;

    private String description;

    private String executionCommand;

    private String riskLevel;
}
