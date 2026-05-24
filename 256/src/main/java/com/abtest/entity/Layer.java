package com.abtest.entity;

import jakarta.persistence.*;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
@Entity
@Table(name = "layers")
public class Layer {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String name;

    @Column(length = 1000)
    private String description;

    @Column(nullable = false)
    private String trafficKey;

    @Column(nullable = false)
    private Integer trafficPercentage = 100;

    @OneToMany(mappedBy = "layer")
    private List<Experiment> experiments = new ArrayList<>();

    @Column(nullable = false)
    private Boolean isActive = true;
}
