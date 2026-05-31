package com.quota.management.controller;

import com.quota.management.common.Result;
import com.quota.management.entity.QuotaUsage;
import com.quota.management.entity.TenantQuota;
import com.quota.management.entity.TransferTransaction;
import com.quota.management.service.QuotaManagementService;
import com.quota.management.service.TokenBucketService.PreConsumeResult;
import com.quota.management.service.WarningService;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/tenant")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class TenantQuotaController {

    private final QuotaManagementService quotaManagementService;
    private final WarningService warningService;

    @PostMapping
    public Result<TenantQuota> createTenantQuota(@RequestBody TenantQuota quota) {
        TenantQuota created = quotaManagementService.createTenantQuota(quota);
        return Result.success(created);
    }

    @GetMapping("/{tenantId}")
    public Result<TenantQuota> getTenantQuota(@PathVariable String tenantId) {
        TenantQuota quota = quotaManagementService.getTenantQuota(tenantId);
        if (quota == null) {
            return Result.error(404, "Tenant not found");
        }
        return Result.success(quota);
    }

    @PutMapping
    public Result<TenantQuota> updateTenantQuota(@RequestBody TenantQuota quota) {
        TenantQuota updated = quotaManagementService.updateTenantQuota(quota);
        return Result.success(updated);
    }

    @DeleteMapping("/{tenantId}")
    public Result<Void> deleteTenantQuota(@PathVariable String tenantId) {
        quotaManagementService.deleteTenantQuota(tenantId);
        return Result.success(null);
    }

    @GetMapping("/list")
    public Result<List<TenantQuota>> getAllTenantQuotas() {
        List<TenantQuota> quotas = quotaManagementService.getAllTenantQuotas();
        return Result.success(quotas);
    }

    @GetMapping("/{tenantId}/usage")
    public Result<QuotaUsage> getQuotaUsage(@PathVariable String tenantId) {
        try {
            QuotaUsage usage = quotaManagementService.getQuotaUsage(tenantId);
            return Result.success(usage);
        } catch (RuntimeException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @GetMapping("/{tenantId}/warnings")
    public Result<List<WarningService.WarningLog>> getWarnings(@PathVariable String tenantId) {
        List<WarningService.WarningLog> warnings = warningService.getRecentWarnings(tenantId);
        return Result.success(warnings);
    }

    @PostMapping("/transfer/try")
    public Result<TransferTransaction> transferQuotaTry(@RequestBody TransferTryRequest request) {
        try {
            TransferTransaction tx = quotaManagementService.transferQuotaTry(
                    request.getFromTenantId(),
                    request.getToTenantId(),
                    request.getGranularity(),
                    request.getAmount()
            );
            return Result.success("TCC Try阶段成功，资源已预留", tx);
        } catch (RuntimeException e) {
            return Result.error(409, e.getMessage());
        }
    }

    @PostMapping("/transfer/confirm")
    public Result<TransferTransaction> transferQuotaConfirm(@RequestBody TransferConfirmRequest request) {
        try {
            TransferTransaction tx = quotaManagementService.transferQuotaConfirm(request.getTransactionId());
            return Result.success("TCC Confirm阶段成功，转移已确认", tx);
        } catch (RuntimeException e) {
            return Result.error(409, e.getMessage());
        }
    }

    @PostMapping("/transfer/cancel")
    public Result<TransferTransaction> transferQuotaCancel(@RequestBody TransferConfirmRequest request) {
        try {
            TransferTransaction tx = quotaManagementService.transferQuotaCancel(request.getTransactionId());
            return Result.success("TCC Cancel阶段成功，转移已回滚", tx);
        } catch (RuntimeException e) {
            return Result.error(409, e.getMessage());
        }
    }

    @GetMapping("/transfer/{transactionId}")
    public Result<TransferTransaction> getTransferTransaction(@PathVariable String transactionId) {
        TransferTransaction tx = quotaManagementService.getTransferTransaction(transactionId);
        if (tx == null) {
            return Result.error(404, "Transaction not found");
        }
        return Result.success(tx);
    }

    @PostMapping("/preconsume")
    public Result<PreConsumeResponse> preConsume(@RequestBody PreConsumeRequest request) {
        try {
            PreConsumeResult result = quotaManagementService.preConsume(
                    request.getTenantId(),
                    request.getGranularity(),
                    request.getAmount()
            );
            PreConsumeResponse response = PreConsumeResponse.builder()
                    .success(result.isSuccess())
                    .failReason(result.getFailReason())
                    .newVersion(result.getNewVersion())
                    .remainingTokens(result.getRemainingTokens())
                    .previousVersion(result.getPreviousVersion())
                    .build();
            return Result.success(response);
        } catch (RuntimeException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @PostMapping("/release")
    public Result<Boolean> releasePreConsumed(@RequestBody PreConsumeRequest request) {
        boolean released = quotaManagementService.releasePreConsumed(
                request.getTenantId(),
                request.getGranularity(),
                request.getAmount()
        );
        return Result.success(released);
    }

    @PostMapping("/confirm")
    public Result<Boolean> confirmPreConsumed(@RequestBody PreConsumeRequest request) {
        boolean confirmed = quotaManagementService.confirmPreConsumed(
                request.getTenantId(),
                request.getGranularity(),
                request.getAmount()
        );
        return Result.success(confirmed);
    }

    @Data
    public static class TransferTryRequest {
        private String fromTenantId;
        private String toTenantId;
        private String granularity;
        private long amount;
    }

    @Data
    public static class TransferConfirmRequest {
        private String transactionId;
    }

    @Data
    public static class PreConsumeRequest {
        private String tenantId;
        private String granularity;
        private long amount;
    }

    @Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class PreConsumeResponse {
        private boolean success;
        private String failReason;
        private long newVersion;
        private long remainingTokens;
        private long previousVersion;
    }
}
