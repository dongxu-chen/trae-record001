package com.quota.management.service;

import com.quota.management.entity.TenantQuota;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class RateLimitService {

    private final TokenBucketService tokenBucketService;
    private final QuotaManagementService quotaManagementService;
    private final WarningService warningService;

    @Value("${quota.downgrade.enabled:true}")
    private boolean downgradeEnabled;

    @Value("${quota.downgrade.max-delay-ms:1000}")
    private long maxDelayMs;

    public RateLimitResult checkAndConsume(String tenantId, long tokens) {
        TenantQuota quota = quotaManagementService.getTenantQuota(tenantId);
        if (quota == null) {
            return RateLimitResult.builder()
                    .allowed(false)
                    .reason("TENANT_NOT_FOUND")
                    .build();
        }

        if (!quota.getEnabled()) {
            return RateLimitResult.builder()
                    .allowed(false)
                    .reason("TENANT_DISABLED")
                    .build();
        }

        boolean minuteOk = tokenBucketService.tryConsume(tenantId, "minute", tokens);
        if (!minuteOk) {
            return handleOverLimit(tenantId, "minute", tokens, quota);
        }

        boolean hourOk = tokenBucketService.tryConsume(tenantId, "hour", tokens);
        if (!hourOk) {
            tokenBucketService.addTokens(tenantId, "minute", tokens);
            return handleOverLimit(tenantId, "hour", tokens, quota);
        }

        boolean dayOk = tokenBucketService.tryConsume(tenantId, "day", tokens);
        if (!dayOk) {
            tokenBucketService.addTokens(tenantId, "minute", tokens);
            tokenBucketService.addTokens(tenantId, "hour", tokens);
            return handleOverLimit(tenantId, "day", tokens, quota);
        }

        warningService.checkAndSendWarning(tenantId);

        return RateLimitResult.builder()
                .allowed(true)
                .reason("OK")
                .build();
    }

    private RateLimitResult handleOverLimit(String tenantId, String granularity, long tokens, TenantQuota quota) {
        log.warn("Rate limit exceeded for tenant: {}, granularity: {}", tenantId, granularity);

        switch (quota.getOverLimitStrategy()) {
            case DOWNGRADE:
                if (downgradeEnabled) {
                    try {
                        long delay = Math.min(100, maxDelayMs);
                        Thread.sleep(delay);
                        return RateLimitResult.builder()
                                .allowed(true)
                                .reason("DOWNGRADED")
                                .downgraded(true)
                                .delayMs(delay)
                                .build();
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                    }
                }
                return RateLimitResult.builder()
                        .allowed(false)
                        .reason("RATE_LIMIT_EXCEEDED")
                        .granularity(granularity)
                        .build();

            case QUEUE:
                return RateLimitResult.builder()
                        .allowed(false)
                        .reason("QUEUE_REQUIRED")
                        .granularity(granularity)
                        .build();

            case REJECT:
            default:
                return RateLimitResult.builder()
                        .allowed(false)
                        .reason("RATE_LIMIT_EXCEEDED")
                        .granularity(granularity)
                        .build();
        }
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class RateLimitResult {
        private boolean allowed;
        private String reason;
        private String granularity;
        private boolean downgraded;
        private long delayMs;
    }
}
