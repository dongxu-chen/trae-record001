package com.medical.stockwarning.controller;

import com.medical.stockwarning.dto.ApiResponse;
import com.medical.stockwarning.dto.WarningDTO;
import com.medical.stockwarning.entity.WarningLog;
import com.medical.stockwarning.enums.WarningType;
import com.medical.stockwarning.service.WarningService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/warnings")
@RequiredArgsConstructor
public class WarningController {

    private final WarningService warningService;

    @GetMapping
    public ApiResponse<List<WarningDTO>> getWarnings(
            @RequestParam(required = false) WarningType type,
            @RequestParam(required = false, defaultValue = "false") boolean resolved) {
        if (resolved) {
            return ApiResponse.success(warningService.getAllWarnings());
        } else if (type != null) {
            return ApiResponse.success(warningService.getWarningsByType(type));
        }
        return ApiResponse.success(warningService.getUnresolvedWarnings());
    }

    @GetMapping("/low-stock")
    public ApiResponse<List<WarningDTO>> getLowStockWarnings() {
        return ApiResponse.success(warningService.getLowStockWarnings());
    }

    @GetMapping("/near-expiry")
    public ApiResponse<List<WarningDTO>> getNearExpiryWarnings() {
        return ApiResponse.success(warningService.getNearExpiryWarnings());
    }

    @GetMapping("/expired")
    public ApiResponse<List<WarningDTO>> getExpiredWarnings() {
        return ApiResponse.success(warningService.getExpiredWarnings());
    }

    @GetMapping("/{warningId}")
    public ApiResponse<WarningLog> getWarningById(@PathVariable Long warningId) {
        return ApiResponse.success(warningService.getWarningById(warningId));
    }

    @PutMapping("/{warningId}/resolve")
    public ApiResponse<WarningLog> resolveWarning(
            @PathVariable Long warningId,
            @RequestParam String resolveBy,
            @RequestParam String resolveNote) {
        return ApiResponse.success(warningService.resolveWarning(warningId, resolveBy, resolveNote));
    }

    @PostMapping("/batch-resolve")
    public ApiResponse<Void> batchResolveWarnings(
            @RequestBody List<Long> warningIds,
            @RequestParam String resolveBy,
            @RequestParam String resolveNote) {
        warningService.batchResolveWarnings(warningIds, resolveBy, resolveNote);
        return ApiResponse.success();
    }

    @GetMapping("/summary")
    public ApiResponse<Map<String, Object>> getWarningSummary() {
        Map<String, Object> summary = new HashMap<>();
        summary.put("totalUnresolved", warningService.countUnresolvedWarnings());
        summary.put("lowStockCount", warningService.countWarningsByType(WarningType.LOW_STOCK));
        summary.put("nearExpiryCount", warningService.countWarningsByType(WarningType.NEAR_EXPIRY));
        summary.put("expiredCount", warningService.countWarningsByType(WarningType.EXPIRED));
        return ApiResponse.success(summary);
    }
}
