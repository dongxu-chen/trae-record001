package com.property.repair.entity;

import lombok.Data;
import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "order_part")
public class OrderPart {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "order_id")
    private Long orderId;

    @Column(name = "order_no", length = 50)
    private String orderNo;

    @Column(name = "part_id")
    private Long partId;

    @Column(name = "part_code", length = 50)
    private String partCode;

    @Column(name = "part_name", length = 100)
    private String partName;

    @Column(length = 200)
    private String specification;

    @Column(name = "unit", length = 20)
    private String unit;

    @Column(name = "unit_price")
    private Double unitPrice;

    private Integer quantity;

    @Column(name = "total_price")
    private Double totalPrice;

    @Column(length = 20)
    private String status;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
        if (status == null) {
            status = "LOCKED";
        }
    }
}
