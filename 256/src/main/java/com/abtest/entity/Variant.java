package com.abtest.entity;

import jakarta.persistence.*;
import lombok.Data;

@Data
@Entity
@Table(name = "variants", uniqueConstraints = {
    @UniqueConstraint(columnNames = {"experiment_id", "name"})
})
public class Variant {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "experiment_id", nullable = false)
    private Experiment experiment;

    @Column(nullable = false)
    private String name;

    @Column(nullable = false)
    private Integer trafficWeight;

    @Column(nullable = false)
    private Boolean isControl;

    private String configuration;
}
