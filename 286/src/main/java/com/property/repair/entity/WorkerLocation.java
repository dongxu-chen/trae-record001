package com.property.repair.entity;

import lombok.Data;
import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "worker_location")
public class WorkerLocation {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "worker_id")
    private Long workerId;

    @Column(name = "worker_name", length = 50)
    private String workerName;

    private Double longitude;

    private Double latitude;

    @Column(length = 200)
    private String address;

    @Column(name = "accuracy")
    private Double accuracy;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
    }
}
