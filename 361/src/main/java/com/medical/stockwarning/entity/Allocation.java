package com.medical.stockwarning.entity;

import com.medical.stockwarning.enums.AllocationStatus;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@Entity
@Table(name = "t_allocation")
public class Allocation extends BaseEntity {

    @Column(name = "allocation_no", nullable = false, length = 32, unique = true)
    private String allocationNo;

    @Column(name = "medicine_id", nullable = false)
    private Long medicineId;

    @Column(name = "from_warehouse_id", nullable = false)
    private Long fromWarehouseId;

    @Column(name = "to_warehouse_id", nullable = false)
    private Long toWarehouseId;

    @Column(name = "quantity", nullable = false)
    private Integer quantity;

    @Column(name = "unit_price", precision = 12, scale = 2)
    private BigDecimal unitPrice;

    @Column(name = "total_amount", precision = 14, scale = 2)
    private BigDecimal totalAmount;

    @Column(name = "reason", length = 500)
    private String reason;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", length = 20)
    private AllocationStatus status = AllocationStatus.PENDING;

    @Column(name = "allocation_date")
    private LocalDateTime allocationDate;
}
