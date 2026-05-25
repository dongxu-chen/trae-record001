package com.property.repair.entity;

import lombok.Data;
import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "repair_order")
public class RepairOrder {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "order_no", unique = true, length = 50)
    private String orderNo;

    @Column(name = "owner_id")
    private Long ownerId;

    @Column(name = "owner_name", length = 50)
    private String ownerName;

    @Column(name = "owner_phone", length = 20)
    private String ownerPhone;

    @Column(name = "repair_type_id")
    private Long repairTypeId;

    @Column(name = "repair_type_name", length = 50)
    private String repairTypeName;

    @Column(name = "address", length = 200)
    private String address;

    @Column(name = "longitude")
    private Double longitude;

    @Column(name = "latitude")
    private Double latitude;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "images", columnDefinition = "TEXT")
    private String images;

    @Column(name = "compressed_images", columnDefinition = "TEXT")
    private String compressedImages;

    @Column(name = "worker_id")
    private Long workerId;

    @Column(name = "worker_name", length = 50)
    private String workerName;

    @Column(name = "worker_phone", length = 20)
    private String workerPhone;

    @Column(length = 20)
    private String status;

    @Column(name = "priority")
    private Integer priority;

    @Column(name = "submit_time")
    private LocalDateTime submitTime;

    @Column(name = "assign_time")
    private LocalDateTime assignTime;

    @Column(name = "accept_time")
    private LocalDateTime acceptTime;

    @Column(name = "complete_time")
    private LocalDateTime completeTime;

    @Column(name = "estimated_hours")
    private Integer estimatedHours;

    @Column(name = "actual_hours")
    private Integer actualHours;

    @Column(name = "feed_back", columnDefinition = "TEXT")
    private String feedBack;

    @Column(name = "remind_count")
    private Integer remindCount;

    @Column(name = "last_remind_time")
    private LocalDateTime lastRemindTime;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
        submitTime = LocalDateTime.now();
        if (status == null) {
            status = "PENDING";
        }
        if (remindCount == null) {
            remindCount = 0;
        }
    }
}
