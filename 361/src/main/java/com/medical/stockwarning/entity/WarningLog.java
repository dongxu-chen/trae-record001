package com.medical.stockwarning.entity;

import com.medical.stockwarning.enums.Severity;
import com.medical.stockwarning.enums.WarningType;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@Entity
@Table(name = "t_warning_log")
public class WarningLog extends BaseEntity {

    @Enumerated(EnumType.STRING)
    @Column(name = "warning_type", nullable = false, length = 30)
    private WarningType warningType;

    @Enumerated(EnumType.STRING)
    @Column(name = "severity", length = 20)
    private Severity severity = Severity.WARNING;

    @Column(name = "warehouse_id")
    private Long warehouseId;

    @Column(name = "medicine_id")
    private Long medicineId;

    @Column(name = "batch_no", length = 64)
    private String batchNo;

    @Column(name = "current_value")
    private Integer currentValue;

    @Column(name = "threshold_value")
    private Integer thresholdValue;

    @Column(name = "message", length = 500)
    private String message;

    @Column(name = "is_resolved")
    private Integer isResolved = 0;

    @Column(name = "resolve_time")
    private LocalDateTime resolveTime;

    @Column(name = "resolve_by", length = 50)
    private String resolveBy;

    @Column(name = "resolve_note", length = 500)
    private String resolveNote;
}
