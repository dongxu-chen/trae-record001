package com.medical.stockwarning.controller;

import com.medical.stockwarning.dto.ApiResponse;
import com.medical.stockwarning.dto.StockAllocationDTO;
import com.medical.stockwarning.entity.Allocation;
import com.medical.stockwarning.optimization.StockAllocationOptimizer;
import com.medical.stockwarning.service.StockAllocationService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/allocations")
@RequiredArgsConstructor
public class AllocationController {

    private final StockAllocationService allocationService;
    private final StockAllocationOptimizer allocationOptimizer;

    @PostMapping
    public ApiResponse<Allocation> createAllocation(@RequestBody StockAllocationDTO dto) {
        return ApiResponse.success(allocationService.createAllocation(dto));
    }

    @PostMapping("/auto-generate")
    public ApiResponse<List<Allocation>> autoGenerateAllocations() {
        return ApiResponse.success(allocationService.createAutoAllocations());
    }

    @PostMapping("/optimize/{medicineId}")
    public ApiResponse<StockAllocationOptimizer.OptimizationResult> optimizeAllocation(
            @PathVariable Long medicineId) {
        return ApiResponse.success(allocationOptimizer.optimizeAllocation(medicineId));
    }

    @PostMapping("/optimize-all")
    public ApiResponse<List<StockAllocationOptimizer.OptimizationResult>> optimizeAllMedicines() {
        return ApiResponse.success(allocationOptimizer.optimizeAllMedicines());
    }

    @GetMapping
    public ApiResponse<List<Allocation>> getAllocations(
            @RequestParam(required = false) Long medicineId,
            @RequestParam(required = false) Long warehouseId,
            @RequestParam(required = false, defaultValue = "pending") String type) {

        if ("outbound".equals(type) && warehouseId != null) {
            return ApiResponse.success(allocationService.getOutboundAllocations(warehouseId));
        } else if ("inbound".equals(type) && warehouseId != null) {
            return ApiResponse.success(allocationService.getInboundAllocations(warehouseId));
        } else if (medicineId != null) {
            return ApiResponse.success(allocationService.getAllocationsByMedicine(medicineId));
        }
        return ApiResponse.success(allocationService.getPendingAllocations());
    }

    @GetMapping("/{allocationId}")
    public ApiResponse<Allocation> getAllocationById(@PathVariable Long allocationId) {
        return ApiResponse.success(allocationService.getAllocationById(allocationId));
    }

    @PutMapping("/{allocationId}/confirm-outbound")
    public ApiResponse<Allocation> confirmOutbound(@PathVariable Long allocationId) {
        return ApiResponse.success(allocationService.confirmOutbound(allocationId));
    }

    @PutMapping("/{allocationId}/confirm-inbound")
    public ApiResponse<Allocation> confirmInbound(@PathVariable Long allocationId) {
        return ApiResponse.success(allocationService.confirmInbound(allocationId));
    }

    @PutMapping("/{allocationId}/cancel")
    public ApiResponse<Allocation> cancelAllocation(
            @PathVariable Long allocationId,
            @RequestParam String reason) {
        return ApiResponse.success(allocationService.cancelAllocation(allocationId, reason));
    }
}
