package com.medical.stockwarning.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
@Builder
public class PurchasePlanDTO {

    private Long medicineId;
    private String medicineName;
    private Long warehouseId;
    private String warehouseName;
    private Integer planQuantity;
    private BigDecimal unitPrice;
    private BigDecimal totalAmount;
    private LocalDate expectedDate;
    private Integer reorderPoint;
    private Integer safetyStock;
    private BigDecimal avgConsumption;
    private Integer leadTimeDays;
    private String remark;
}
