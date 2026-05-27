package com.medical.stockwarning.dto;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDate;

@Data
@Builder
public class MedicineStockDTO {

    private Long medicineId;
    private String medicineCode;
    private String medicineName;
    private String specification;
    private String manufacturer;
    private String unit;
    private Long warehouseId;
    private String warehouseName;
    private Integer totalQuantity;
    private Integer availableQuantity;
    private Integer lockedQuantity;
    private LocalDate earliestExpiryDate;
    private Integer nearExpiryCount;
    private Integer expiredCount;
    private Boolean hasWarning;
}
