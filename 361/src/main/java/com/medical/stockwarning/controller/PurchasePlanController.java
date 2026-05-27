package com.medical.stockwarning.controller;

import com.medical.stockwarning.dto.ApiResponse;
import com.medical.stockwarning.dto.PurchasePlanDTO;
import com.medical.stockwarning.entity.PurchasePlan;
import com.medical.stockwarning.enums.ApprovalStatus;
import com.medical.stockwarning.enums.PurchaseStatus;
import com.medical.stockwarning.service.PurchasePlanService;
import com.medical.stockwarning.service.ReorderCalculationService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/purchase-plans")
@RequiredArgsConstructor
public class PurchasePlanController {

    private final PurchasePlanService purchasePlanService;
    private final ReorderCalculationService reorderCalculationService;

    @PostMapping
    public ApiResponse<PurchasePlan> generatePurchasePlan(@RequestBody PurchasePlanDTO planDTO) {
        return ApiResponse.success(purchasePlanService.generatePurchasePlan(planDTO));
    }

    @PostMapping("/auto-generate")
    public ApiResponse<List<PurchasePlan>> autoGeneratePurchasePlans() {
        return ApiResponse.success(purchasePlanService.generatePurchasePlansForLowStock());
    }

    @GetMapping
    public ApiResponse<List<PurchasePlan>> getPlans(
            @RequestParam(required = false) PurchaseStatus status,
            @RequestParam(required = false) ApprovalStatus approvalStatus) {
        if (status != null) {
            return ApiResponse.success(purchasePlanService.getPlansByStatus(status));
        } else if (approvalStatus != null) {
            return ApiResponse.success(purchasePlanService.getPlansByApprovalStatus(approvalStatus));
        }
        return ApiResponse.success(purchasePlanService.getPendingApprovalPlans());
    }

    @GetMapping("/{planId}")
    public ApiResponse<PurchasePlan> getPlanById(@PathVariable Long planId) {
        return ApiResponse.success(purchasePlanService.getPlanById(planId));
    }

    @GetMapping("/warehouse/{warehouseId}")
    public ApiResponse<List<PurchasePlan>> getPlansByWarehouse(@PathVariable Long warehouseId) {
        return ApiResponse.success(purchasePlanService.getPlansByWarehouse(warehouseId));
    }

    @GetMapping("/pending-approval")
    public ApiResponse<List<PurchasePlan>> getPendingApprovalPlans() {
        return ApiResponse.success(purchasePlanService.getPendingApprovalPlans());
    }

    @PutMapping("/{planId}/approve")
    public ApiResponse<PurchasePlan> approvePlan(
            @PathVariable Long planId,
            @RequestParam String approver) {
        return ApiResponse.success(purchasePlanService.approvePlan(planId, approver));
    }

    @PutMapping("/{planId}/reject")
    public ApiResponse<PurchasePlan> rejectPlan(
            @PathVariable Long planId,
            @RequestParam String approver,
            @RequestParam String reason) {
        return ApiResponse.success(purchasePlanService.rejectPlan(planId, approver, reason));
    }

    @PutMapping("/{planId}/place-order")
    public ApiResponse<PurchasePlan> placeOrder(@PathVariable Long planId) {
        return ApiResponse.success(purchasePlanService.placeOrder(planId));
    }

    @PutMapping("/{planId}/confirm-receipt")
    public ApiResponse<PurchasePlan> confirmReceipt(
            @PathVariable Long planId,
            @RequestParam Integer actualQuantity) {
        return ApiResponse.success(purchasePlanService.confirmReceipt(planId, actualQuantity));
    }

    @PutMapping("/{planId}/cancel")
    public ApiResponse<PurchasePlan> cancelPlan(
            @PathVariable Long planId,
            @RequestParam String reason) {
        return ApiResponse.success(purchasePlanService.cancelPlan(planId, reason));
    }

    @GetMapping("/date-range")
    public ApiResponse<List<PurchasePlan>> getPlansByDateRange(
            @RequestParam LocalDate startDate,
            @RequestParam LocalDate endDate) {
        return ApiResponse.success(purchasePlanService.getPlansByDateRange(startDate, endDate));
    }

    @PostMapping("/refresh-cache")
    public ApiResponse<Void> refreshCache() {
        reorderCalculationService.refreshCache();
        return ApiResponse.success();
    }
}
