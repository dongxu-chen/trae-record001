package com.medical.stockwarning.controller;

import com.medical.stockwarning.dto.ApiResponse;
import com.medical.stockwarning.dto.SupplierOrderDTO;
import com.medical.stockwarning.service.SupplierIntegrationService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/supplier")
@RequiredArgsConstructor
public class SupplierIntegrationController {

    private final SupplierIntegrationService supplierIntegrationService;

    @PostMapping("/orders/generate")
    public ApiResponse<List<SupplierOrderDTO>> generateOrdersBySupplier() {
        return ApiResponse.success(supplierIntegrationService.generateOrdersBySupplier());
    }

    @PostMapping("/orders/generate-associated/{medicineId}")
    public ApiResponse<List<SupplierOrderDTO>> generateAssociatedOrders(
            @PathVariable Long medicineId,
            @RequestParam Long warehouseId) {
        return ApiResponse.success(supplierIntegrationService.generateAssociatedOrders(medicineId, warehouseId));
    }

    @PostMapping("/orders/generate-forecast")
    public ApiResponse<List<SupplierOrderDTO>> generateForecastBasedOrders(
            @RequestParam Long warehouseId) {
        return ApiResponse.success(supplierIntegrationService.generateForecastBasedOrders(warehouseId));
    }

    @PostMapping("/orders/send")
    public ApiResponse<SupplierOrderDTO> sendOrder(@RequestBody SupplierOrderDTO order) {
        return ApiResponse.success(supplierIntegrationService.sendOrderToSupplier(order));
    }

    @PostMapping("/orders/send-all")
    public ApiResponse<List<SupplierOrderDTO>> sendAllPendingOrders() {
        return ApiResponse.success(supplierIntegrationService.sendAllPendingOrders());
    }

    @GetMapping("/orders/{orderNo}/status")
    public ApiResponse<SupplierOrderDTO> queryOrderStatus(@PathVariable String orderNo) {
        SupplierOrderDTO status = supplierIntegrationService.querySupplierOrderStatus(orderNo);
        if (status != null) {
            return ApiResponse.success(status);
        }
        return ApiResponse.error("Failed to query order status");
    }

    @GetMapping("/integration-status")
    public ApiResponse<Map<String, Object>> getIntegrationStatus() {
        return ApiResponse.success(supplierIntegrationService.getSupplierIntegrationStatus());
    }
}
