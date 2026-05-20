package com.smartschedule.entity;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "notifications")
public class Notification {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "employee_id")
    private Employee employee;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "schedule_id")
    private Schedule schedule;

    @Column(nullable = false, length = 200)
    private String title;

    @Column(length = 1000)
    private String content;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private NotificationType type;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private NotificationChannel channel;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private NotificationStatus status;

    private LocalDateTime sentAt;

    private LocalDateTime createdAt;

    @Column(length = 500)
    private String errorMessage;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        status = NotificationStatus.PENDING;
    }

    public enum NotificationType {
        SCHEDULE_PUBLISHED,
        SCHEDULE_UPDATED,
        SHIFT_CHANGED,
        CONFLICT_DETECTED,
        REMINDER
    }

    public enum NotificationChannel {
        APP_PUSH,
        EMAIL,
        SMS,
        WECHAT
    }

    public enum NotificationStatus {
        PENDING,
        SENT,
        FAILED
    }
}
