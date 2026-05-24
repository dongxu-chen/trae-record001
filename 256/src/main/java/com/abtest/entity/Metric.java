package com.abtest.entity;

import jakarta.persistence.*;
import lombok.Data;

@Data
@Entity
@Table(name = "metrics", uniqueConstraints = {
    @UniqueConstraint(columnNames = {"experiment_id", "name"})
})
public class Metric {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "experiment_id", nullable = false)
    private Experiment experiment;

    @Column(nullable = false)
    private String name;

    @Column(length = 1000)
    private String description;

    @Column(nullable = false)
    @Enumerated(EnumType.STRING)
    private MetricType type;

    @Column(nullable = false)
    private String eventName;

    private String propertyName;

    @Enumerated(EnumType.STRING)
    private AggregationType aggregationType;

    public enum MetricType {
        CONVERSION, CONTINUOUS
    }

    public enum AggregationType {
        SUM, AVG, COUNT, DISTINCT_COUNT
    }
}
