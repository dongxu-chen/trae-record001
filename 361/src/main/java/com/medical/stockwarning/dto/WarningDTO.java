package com.medical.stockwarning.dto;

import com.medical.stockwarning.enums.Severity;
import com.medical.stockwarning.enums.WarningType;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class WarningDTO {

    private Long id;
    private WarningType warningType;
    private Severity severity;
    private Long warehouseId;
    private String warehouseName;
    private Long medicineId;
    private String medicineName;
    private String batchNo;
    private Integer currentValue;
    private Integer thresholdValue;
    private String message;
    private Boolean resolved;
    private LocalDateTime createTime;
}
