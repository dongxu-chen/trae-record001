package com.alert.entity;

import com.alert.enums.AlertSeverity;
import com.alert.enums.AlertStatus;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "alert_event")
public class AlertEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "alert_id", unique = true, nullable = false, length = 64)
    private String alertId;

    @Column(nullable = false, length = 255)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String content;

    @Column(nullable = false, length = 20)
    @Enumerated(EnumType.STRING)
    private AlertSeverity severity;

    @Column(nullable = false, length = 20)
    @Enumerated(EnumType.STRING)
    private AlertStatus status = AlertStatus.NEW;

    @Column(length = 100)
    private String source;

    @Column(length = 100)
    private String host;

    @Column(length = 100)
    private String service;

    @Column(length = 500)
    private String tags;

    @Column(name = "aggregation_key", length = 255)
    private String aggregationKey;

    @Column(name = "parent_alert_id", length = 64)
    private String parentAlertId;

    @Column(length = 50)
    private String assignee;

    @Column(name = "acknowledge_time")
    private LocalDateTime acknowledgeTime;

    @Column(name = "resolve_time")
    private LocalDateTime resolveTime;

    @Column(name = "close_time")
    private LocalDateTime closeTime;

    @Column(name = "upgrade_count")
    private Integer upgradeCount = 0;

    @Column(name = "next_upgrade_time")
    private LocalDateTime nextUpgradeTime;

    @CreationTimestamp
    @Column(name = "create_time", nullable = false, updatable = false)
    private LocalDateTime createTime;

    @UpdateTimestamp
    @Column(name = "update_time", nullable = false)
    private LocalDateTime updateTime;
}
