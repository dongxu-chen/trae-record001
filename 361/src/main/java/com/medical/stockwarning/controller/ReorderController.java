package com.medical.stockwarning.controller;

import com.medical.stockwarning.dto.ApiResponse;
import com.medical.stockwarning.dto.ReorderPointDTO;
import com.medical.stockwarning.service.ReorderCalculationService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/reorder")
@RequiredArgsConstructor
public class ReorderController {

    private final ReorderCalculationService reorderCalculationService;

    @GetMapping("/warehouse/{warehouseId}/medicine/{medicineId}")
    public ApiResponse<ReorderPointDTO> calculateReorderPoint(
            @PathVariable Long warehouseId,
            @PathVariable Long medicineId) {
        return ApiResponse.success(reorderCalculationService.calculateReorderPoint(warehouseId, medicineId));
    }

    @GetMapping("/warehouse/{warehouseId}")
    public ApiResponse<List<ReorderPointDTO>> calculateReorderPointsForWarehouse(
            @PathVariable Long warehouseId) {
        return ApiResponse.success(reorderCalculationService.calculateReorderPointsForWarehouse(warehouseId));
    }

    @GetMapping("/all")
    public ApiResponse<List<ReorderPointDTO>> calculateAllReorderPoints() {
        return ApiResponse.success(reorderCalculationService.calculateAllReorderPoints());
    }

    @GetMapping("/low-stock")
    public ApiResponse<List<ReorderPointDTO>> getLowStockItems() {
        return ApiResponse.success(reorderCalculationService.getLowStockItems());
    }

    @GetMapping("/critical-stock")
    public ApiResponse<List<ReorderPointDTO>> getCriticalStockItems() {
        return ApiResponse.success(reorderCalculationService.getCriticalStockItems());
    }

    @GetMapping("/warehouse/{warehouseId}/medicine/{medicineId}/purchase-quantity")
    public ApiResponse<Integer> calculatePurchaseQuantity(
            @PathVariable Long warehouseId,
            @PathVariable Long medicineId) {
        return ApiResponse.success(reorderCalculationService.calculatePurchaseQuantity(warehouseId, medicineId));
    }

    @GetMapping("/service-level")
    public ApiResponse<Double> getServiceLevel() {
        return ApiResponse.success(reorderCalculationService.getServiceLevel());
    }

    @PutMapping("/service-level")
    public ApiResponse<Void> setServiceLevel(@RequestParam double serviceLevel) {
        reorderCalculationService.setServiceLevel(serviceLevel);
        reorderCalculationService.refreshCache();
        return ApiResponse.success();
    }

    @GetMapping("/config")
    public ApiResponse<Map<String, Object>> getReorderConfig() {
        Map<String, Object> config = new HashMap<>();
        config.put("serviceLevel", reorderCalculationService.getServiceLevel());
        return ApiResponse.success(config);
    }

    @PostMapping("/refresh-cache")
    public ApiResponse<Void> refreshCache() {
        reorderCalculationService.refreshCache();
        return ApiResponse.success();
    }
}
