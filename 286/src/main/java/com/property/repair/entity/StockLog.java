package com.property.repair.entity;

import lombok.Data;
import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "stock_log")
public class StockLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "part_id")
    private Long partId;

    @Column(name = "part_code", length = 50)
    private String partCode;

    @Column(name = "part_name", length = 100)
    private String partName;

    @Column(length = 50)
    private String action;

    @Column(name = "change_quantity")
    private Integer changeQuantity;

    @Column(name = "before_quantity")
    private Integer beforeQuantity;

    @Column(name = "after_quantity")
    private Integer afterQuantity;

    @Column(name = "order_id")
    private Long orderId;

    @Column(name = "operator_id")
    private Long operatorId;

    @Column(name = "operator_name", length = 50)
    private String operatorName;

    @Column(length = 500)
    private String remark;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
    }
}
