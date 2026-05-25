package com.alert.entity;

import com.alert.enums.AlertSeverity;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "alert_aggregation")
public class AlertAggregation {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "aggregation_key", unique = true, nullable = false, length = 255)
    private String aggregationKey;

    @Column(nullable = false, length = 255)
    private String title;

    @Column(nullable = false, length = 20)
    @Enumerated(EnumType.STRING)
    private AlertSeverity severity;

    @Column(nullable = false)
    private Integer count = 1;

    @Column(nullable = false, length = 20)
    private String status = "ACTIVE";

    @Column(name = "first_alert_time", nullable = false)
    private LocalDateTime firstAlertTime;

    @Column(name = "last_alert_time", nullable = false)
    private LocalDateTime lastAlertTime;

    @CreationTimestamp
    @Column(name = "create_time", nullable = false, updatable = false)
    private LocalDateTime createTime;

    @UpdateTimestamp
    @Column(name = "update_time", nullable = false)
    private LocalDateTime updateTime;
}
