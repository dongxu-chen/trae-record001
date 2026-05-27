package com.medical.stockwarning.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@Entity
@Table(name = "t_stock")
public class Stock extends BaseEntity {

    @Column(name = "warehouse_id", nullable = false)
    private Long warehouseId;

    @Column(name = "medicine_id", nullable = false)
    private Long medicineId;

    @Column(name = "batch_no", nullable = false, length = 64)
    private String batchNo;

    @Column(name = "quantity", nullable = false)
    private Integer quantity = 0;

    @Column(name = "locked_quantity", nullable = false)
    private Integer lockedQuantity = 0;

    @Column(name = "unit_price", nullable = false, precision = 12, scale = 2)
    private BigDecimal unitPrice = BigDecimal.ZERO;

    @Column(name = "production_date")
    private LocalDate productionDate;

    @Column(name = "expiry_date", nullable = false)
    private LocalDate expiryDate;

    @Column(name = "supplier_id")
    private Long supplierId;

    @Column(name = "inbound_date")
    private LocalDateTime inboundDate;

    @Column(name = "is_expired")
    private Integer isExpired = 0;

    @Column(name = "is_blocked")
    private Integer isBlocked = 0;

    public Integer getAvailableQuantity() {
        return quantity - lockedQuantity;
    }
}
