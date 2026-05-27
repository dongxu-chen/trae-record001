package com.medical.stockwarning.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

@Data
@Builder
public class SupplierOrderDTO {

    private String orderNo;
    private Long supplierId;
    private String supplierName;
    private String supplierCode;
    private Long warehouseId;
    private String warehouseName;
    private LocalDate orderDate;
    private LocalDate expectedDeliveryDate;
    private BigDecimal totalAmount;
    private Integer totalItems;
    private String status;
    private String supplierSystemRef;
    private String orderType;
    private List<OrderItem> items;
    private String remark;

    @Data
    @Builder
    public static class OrderItem {
        private Long medicineId;
        private String medicineCode;
        private String medicineName;
        private String specification;
        private Integer quantity;
        private BigDecimal unitPrice;
        private BigDecimal totalAmount;
        private LocalDate expectedDeliveryDate;
    }
}
