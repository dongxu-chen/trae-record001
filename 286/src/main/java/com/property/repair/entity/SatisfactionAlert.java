package com.property.repair.entity;

import lombok.Data;
import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "satisfaction_alert")
public class SatisfactionAlert {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "worker_id")
    private Long workerId;

    @Column(name = "worker_name", length = 50)
    private String workerName;

    @Column(name = "alert_type", length = 50)
    private String alertType;

    @Column(name = "alert_level", length = 20)
    private String alertLevel;

    @Column(name = "order_id")
    private Long orderId;

    @Column(name = "order_no", length = 50)
    private String orderNo;

    private Integer rating;

    @Column(length = 500)
    private String comment;

    @Column(length = 20)
    private String status;

    @Column(length = 500)
    private String remark;

    @Column(name = "handler_id")
    private Long handlerId;

    @Column(name = "handler_name", length = 50)
    private String handlerName;

    @Column(name = "handle_time")
    private LocalDateTime handleTime;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
        if (status == null) {
            status = "PENDING";
        }
    }
}
