package com.property.repair.entity;

import lombok.Data;
import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "spare_part")
public class SparePart {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "part_code", unique = true, length = 50)
    private String partCode;

    @Column(name = "part_name", length = 100)
    private String partName;

    @Column(length = 200)
    private String specification;

    @Column(length = 100)
    private String category;

    @Column(name = "unit", length = 20)
    private String unit;

    @Column(name = "unit_price")
    private Double unitPrice;

    @Column(name = "stock_quantity")
    private Integer stockQuantity;

    @Column(name = "locked_quantity")
    private Integer lockedQuantity;

    @Column(name = "safe_stock")
    private Integer safeStock;

    @Column(length = 200)
    private String location;

    @Column(length = 500)
    private String description;

    private Integer status;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @Column(name = "update_time")
    private LocalDateTime updateTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
        updateTime = LocalDateTime.now();
        if (status == null) {
            status = 1;
        }
        if (stockQuantity == null) {
            stockQuantity = 0;
        }
        if (lockedQuantity == null) {
            lockedQuantity = 0;
        }
        if (safeStock == null) {
            safeStock = 10;
        }
    }

    @PreUpdate
    protected void onUpdate() {
        updateTime = LocalDateTime.now();
    }

    public Integer getAvailableQuantity() {
        return stockQuantity - lockedQuantity;
    }
}
