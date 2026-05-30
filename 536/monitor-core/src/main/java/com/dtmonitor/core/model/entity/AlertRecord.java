package com.dtmonitor.core.model.entity;

import com.dtmonitor.core.enums.AlertLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "alert_record")
public class AlertRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "alert_name", length = 128)
    private String alertName;

    @Column(name = "xid", length = 64)
    private String xid;

    @Column(name = "branch_id", length = 64)
    private String branchId;

    @Enumerated(EnumType.STRING)
    @Column(length = 16)
    private AlertLevel level;

    @Column(name = "alert_rule", length = 256)
    private String alertRule;

    @Column(length = 2048)
    private String message;

    @Column(name = "is_acknowledged")
    private Boolean acknowledged;

    @Column(name = "acknowledged_by", length = 64)
    private String acknowledgedBy;

    @Column(name = "acknowledged_at")
    private LocalDateTime acknowledgedAt;

    @Column(name = "triggered_at")
    private LocalDateTime triggeredAt;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        if (triggeredAt == null) {
            triggeredAt = LocalDateTime.now();
        }
        if (acknowledged == null) {
            acknowledged = false;
        }
    }
}
