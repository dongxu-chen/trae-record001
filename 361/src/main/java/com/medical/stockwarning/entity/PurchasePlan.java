package com.medical.stockwarning.entity;

import com.medical.stockwarning.enums.ApprovalStatus;
import com.medical.stockwarning.enums.PurchaseStatus;
import jakarta.persistence.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@Entity
@Table(name = "t_purchase_plan")
public class PurchasePlan extends BaseEntity {

    @Column(name = "plan_no", nullable = false, length = 32, unique = true)
    private String planNo;

    @Column(name = "medicine_id", nullable = false)
    private Long medicineId;

    @Column(name = "supplier_id")
    private Long supplierId;

    @Column(name = "warehouse_id", nullable = false)
    private Long warehouseId;

    @Column(name = "plan_quantity", nullable = false)
    private Integer planQuantity;

    @Column(name = "actual_quantity")
    private Integer actualQuantity = 0;

    @Column(name = "unit_price", precision = 12, scale = 2)
    private BigDecimal unitPrice;

    @Column(name = "total_amount", precision = 14, scale = 2)
    private BigDecimal totalAmount;

    @Column(name = "expected_date")
    private LocalDate expectedDate;

    @Column(name = "reorder_point")
    private Integer reorderPoint;

    @Column(name = "safety_stock")
    private Integer safetyStock;

    @Column(name = "avg_consumption", precision = 10, scale = 2)
    private BigDecimal avgConsumption;

    @Column(name = "lead_time_days")
    private Integer leadTimeDays;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", length = 20)
    private PurchaseStatus status = PurchaseStatus.PENDING;

    @Enumerated(EnumType.STRING)
    @Column(name = "approval_status", length = 20)
    private ApprovalStatus approvalStatus = ApprovalStatus.PENDING;

    @Column(name = "plan_date")
    private LocalDate planDate;

    @Column(name = "order_date")
    private LocalDateTime orderDate;

    @Column(name = "receipt_date")
    private LocalDateTime receiptDate;

    @Column(name = "approver", length = 50)
    private String approver;

    @Column(name = "approval_time")
    private LocalDateTime approvalTime;

    @Column(name = "remark", length = 500)
    private String remark;
}
