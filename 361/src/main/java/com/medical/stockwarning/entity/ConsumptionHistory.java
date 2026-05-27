package com.medical.stockwarning.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
@EqualsAndHashCode(callSuper = true)
@Entity
@Table(name = "t_consumption_history")
public class ConsumptionHistory extends BaseEntity {

    @Column(name = "warehouse_id", nullable = false)
    private Long warehouseId;

    @Column(name = "medicine_id", nullable = false)
    private Long medicineId;

    @Column(name = "quantity", nullable = false)
    private Integer quantity;

    @Column(name = "consumption_date", nullable = false)
    private LocalDate consumptionDate;

    @Column(name = "unit_price", precision = 12, scale = 2)
    private BigDecimal unitPrice;

    @Column(name = "total_amount", precision = 14, scale = 2)
    private BigDecimal totalAmount;

    @Column(name = "department", length = 100)
    private String department;

    @Column(name = "remark", length = 500)
    private String remark;
}
