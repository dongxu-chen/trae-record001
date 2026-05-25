package com.property.repair.entity;

import lombok.Data;
import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "repair_type")
public class RepairType {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "type_name", length = 50)
    private String typeName;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "estimated_hours")
    private Integer estimatedHours;

    private Integer priority;

    @Column(name = "remind_minutes")
    private Integer remindMinutes;

    @Column(name = "is_emergency")
    private Boolean isEmergency;

    private Integer status;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
        if (status == null) {
            status = 1;
        }
        if (priority == null) {
            priority = 1;
        }
    }
}
