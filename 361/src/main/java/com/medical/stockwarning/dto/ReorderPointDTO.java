package com.medical.stockwarning.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;

@Data
@Builder
public class ReorderPointDTO {

    private Long medicineId;
    private Long warehouseId;
    private Integer reorderPoint;
    private Integer safetyStock;
    private BigDecimal avgDailyConsumption;
    private Integer leadTimeDays;
    private Integer currentStock;
    private Integer maxStock;
    private String medicineName;
    private String warehouseName;
    private Double serviceLevel;
    private Double zValue;
    private BigDecimal stdDevConsumption;
}
