package com.property.repair.entity;

import lombok.Data;
import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "repair_worker")
public class RepairWorker {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "worker_id", unique = true)
    private Long workerId;

    @Column(length = 200)
    private String skills;

    @Column(name = "current_workload")
    private Integer currentWorkload;

    @Column(name = "avg_rating")
    private Double avgRating;

    @Column(name = "total_orders")
    private Integer totalOrders;

    @Column(name = "work_area")
    private String workArea;

    @Column(name = "longitude")
    private Double longitude;

    @Column(name = "latitude")
    private Double latitude;

    @Column(name = "consecutive_low_ratings")
    private Integer consecutiveLowRatings;

    @Column(name = "need_training")
    private Boolean needTraining;

    @Column(name = "training_start_time")
    private LocalDateTime trainingStartTime;

    @Column(name = "training_end_time")
    private LocalDateTime trainingEndTime;

    private Integer status;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
        if (currentWorkload == null) {
            currentWorkload = 0;
        }
        if (status == null) {
            status = 1;
        }
    }
}
