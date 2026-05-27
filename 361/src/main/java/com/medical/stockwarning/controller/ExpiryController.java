package com.medical.stockwarning.controller;

import com.medical.stockwarning.dto.ApiResponse;
import com.medical.stockwarning.entity.Stock;
import com.medical.stockwarning.service.ExpiryWarningService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/expiry")
@RequiredArgsConstructor
public class ExpiryController {

    private final ExpiryWarningService expiryWarningService;

    @PostMapping("/check")
    public ApiResponse<Void> runExpiryCheck() {
        expiryWarningService.runFullExpiryCheck();
        return ApiResponse.success();
    }

    @PostMapping("/check-expired")
    public ApiResponse<Void> checkExpiredStocks() {
        expiryWarningService.checkAndMarkExpiredStocks();
        return ApiResponse.success();
    }

    @PostMapping("/check-near-expiry")
    public ApiResponse<Void> checkNearExpiryStocks() {
        expiryWarningService.checkAndBlockNearExpiryStocks();
        return ApiResponse.success();
    }

    @PostMapping("/deactivate-expired")
    public ApiResponse<Void> deactivateExpiredMedicines() {
        expiryWarningService.deactivateExpiredMedicines();
        return ApiResponse.success();
    }

    @GetMapping("/expired")
    public ApiResponse<List<Stock>> getExpiredStocks(
            @RequestParam(required = false) Long warehouseId) {
        return ApiResponse.success(expiryWarningService.getExpiredStocks(warehouseId));
    }

    @GetMapping("/near-expiry")
    public ApiResponse<List<Stock>> getNearExpiryStocks(
            @RequestParam(required = false) Long warehouseId) {
        return ApiResponse.success(expiryWarningService.getNearExpiryStocks(warehouseId));
    }

    @GetMapping("/high-value-near-expiry")
    public ApiResponse<List<Stock>> getHighValueNearExpiryStocks(
            @RequestParam(required = false) Long warehouseId) {
        return ApiResponse.success(expiryWarningService.getHighValueNearExpiryStocks(warehouseId));
    }

    @GetMapping("/near-expiry-days")
    public ApiResponse<Integer> getNearExpiryDays() {
        return ApiResponse.success(expiryWarningService.getNearExpiryDays());
    }

    @PutMapping("/near-expiry-days")
    public ApiResponse<Void> setNearExpiryDays(@RequestParam int days) {
        expiryWarningService.setNearExpiryDays(days);
        return ApiResponse.success();
    }

    @GetMapping("/value-weight-threshold")
    public ApiResponse<BigDecimal> getValueWeightThreshold() {
        return ApiResponse.success(expiryWarningService.getValueWeightThreshold());
    }

    @PutMapping("/value-weight-threshold")
    public ApiResponse<Void> setValueWeightThreshold(@RequestParam BigDecimal threshold) {
        expiryWarningService.setValueWeightThreshold(threshold);
        return ApiResponse.success();
    }

    @GetMapping("/high-value-extra-days")
    public ApiResponse<Integer> getHighValueExtraDays() {
        return ApiResponse.success(expiryWarningService.getHighValueExtraDays());
    }

    @PutMapping("/high-value-extra-days")
    public ApiResponse<Void> setHighValueExtraDays(@RequestParam int days) {
        expiryWarningService.setHighValueExtraDays(days);
        return ApiResponse.success();
    }

    @GetMapping("/config")
    public ApiResponse<Map<String, Object>> getExpiryConfig() {
        Map<String, Object> config = new HashMap<>();
        config.put("nearExpiryDays", expiryWarningService.getNearExpiryDays());
        config.put("valueWeightThreshold", expiryWarningService.getValueWeightThreshold());
        config.put("highValueExtraDays", expiryWarningService.getHighValueExtraDays());
        return ApiResponse.success(config);
    }
}
