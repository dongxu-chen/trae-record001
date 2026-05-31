package com.quota.management.service;

import com.quota.management.entity.QuotaUsage;
import com.quota.management.entity.TenantQuota;
import com.quota.management.entity.TransferTransaction;
import com.quota.management.service.TokenBucketService.PreConsumeResult;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class QuotaManagementService {

    private static final String TENANT_QUOTA_PREFIX = "quota:tenant:";
    private static final String TENANT_SET_KEY = "quota:tenants:all";

    private final RedisTemplate<String, Object> redisTemplate;
    private final TokenBucketService tokenBucketService;
    private final TccTransferService tccTransferService;

    public TenantQuota createTenantQuota(TenantQuota quota) {
        quota.setCreatedAt(LocalDateTime.now());
        quota.setUpdatedAt(LocalDateTime.now());
        if (quota.getEnabled() == null) {
            quota.setEnabled(true);
        }
        if (quota.getWarningThreshold() == null) {
            quota.setWarningThreshold(0.8);
        }
        if (quota.getOverLimitStrategy() == null) {
            quota.setOverLimitStrategy(TenantQuota.OverLimitStrategy.REJECT);
        }

        String key = TENANT_QUOTA_PREFIX + quota.getTenantId();
        redisTemplate.opsForValue().set(key, quota);
        redisTemplate.opsForSet().add(TENANT_SET_KEY, quota.getTenantId());

        initTokenBuckets(quota);

        log.info("Created tenant quota for tenantId: {}", quota.getTenantId());
        return quota;
    }

    private void initTokenBuckets(TenantQuota quota) {
        if (quota.getMinuteLimit() != null && quota.getMinuteLimit() > 0) {
            tokenBucketService.createBucket(quota.getTenantId(), "minute",
                    quota.getMinuteLimit(), quota.getMinuteLimit() / 60);
        }
        if (quota.getHourLimit() != null && quota.getHourLimit() > 0) {
            tokenBucketService.createBucket(quota.getTenantId(), "hour",
                    quota.getHourLimit(), quota.getHourLimit() / 3600);
        }
        if (quota.getDayLimit() != null && quota.getDayLimit() > 0) {
            tokenBucketService.createBucket(quota.getTenantId(), "day",
                    quota.getDayLimit(), quota.getDayLimit() / 86400);
        }
    }

    public TenantQuota getTenantQuota(String tenantId) {
        String key = TENANT_QUOTA_PREFIX + tenantId;
        Object obj = redisTemplate.opsForValue().get(key);
        if (obj instanceof TenantQuota) {
            return (TenantQuota) obj;
        }
        return null;
    }

    public TenantQuota updateTenantQuota(TenantQuota quota) {
        TenantQuota existing = getTenantQuota(quota.getTenantId());
        if (existing == null) {
            throw new RuntimeException("Tenant quota not found");
        }

        quota.setCreatedAt(existing.getCreatedAt());
        quota.setUpdatedAt(LocalDateTime.now());

        String key = TENANT_QUOTA_PREFIX + quota.getTenantId();
        redisTemplate.opsForValue().set(key, quota);

        tokenBucketService.deleteBucket(quota.getTenantId(), "minute");
        tokenBucketService.deleteBucket(quota.getTenantId(), "hour");
        tokenBucketService.deleteBucket(quota.getTenantId(), "day");
        initTokenBuckets(quota);

        log.info("Updated tenant quota for tenantId: {}", quota.getTenantId());
        return quota;
    }

    public void deleteTenantQuota(String tenantId) {
        String key = TENANT_QUOTA_PREFIX + tenantId;
        redisTemplate.delete(key);
        redisTemplate.opsForSet().remove(TENANT_SET_KEY, tenantId);

        tokenBucketService.deleteBucket(tenantId, "minute");
        tokenBucketService.deleteBucket(tenantId, "hour");
        tokenBucketService.deleteBucket(tenantId, "day");

        log.info("Deleted tenant quota for tenantId: {}", tenantId);
    }

    public List<TenantQuota> getAllTenantQuotas() {
        Set<Object> tenantIds = redisTemplate.opsForSet().members(TENANT_SET_KEY);
        if (tenantIds == null || tenantIds.isEmpty()) {
            return List.of();
        }

        return tenantIds.stream()
                .map(id -> getTenantQuota(String.valueOf(id)))
                .filter(q -> q != null)
                .collect(Collectors.toList());
    }

    public QuotaUsage getQuotaUsage(String tenantId) {
        TenantQuota quota = getTenantQuota(tenantId);
        if (quota == null) {
            throw new RuntimeException("Tenant quota not found");
        }

        long minuteUsed = quota.getMinuteLimit() - tokenBucketService.getAvailableTokens(tenantId, "minute");
        long hourUsed = quota.getHourLimit() - tokenBucketService.getAvailableTokens(tenantId, "hour");
        long dayUsed = quota.getDayLimit() - tokenBucketService.getAvailableTokens(tenantId, "day");

        return QuotaUsage.builder()
                .tenantId(tenantId)
                .minuteUsed(Math.max(0, minuteUsed))
                .hourUsed(Math.max(0, hourUsed))
                .dayUsed(Math.max(0, dayUsed))
                .minuteRemaining(Math.max(0, quota.getMinuteLimit() - minuteUsed))
                .hourRemaining(Math.max(0, quota.getHourLimit() - hourUsed))
                .dayRemaining(Math.max(0, quota.getDayLimit() - dayUsed))
                .minuteUsageRate(quota.getMinuteLimit() > 0 ? (double) minuteUsed / quota.getMinuteLimit() : 0)
                .hourUsageRate(quota.getHourLimit() > 0 ? (double) hourUsed / quota.getHourLimit() : 0)
                .dayUsageRate(quota.getDayLimit() > 0 ? (double) dayUsed / quota.getDayLimit() : 0)
                .build();
    }

    public TransferTransaction transferQuotaTry(String fromTenantId, String toTenantId, String granularity, long amount) {
        TenantQuota fromQuota = getTenantQuota(fromTenantId);
        TenantQuota toQuota = getTenantQuota(toTenantId);
        if (fromQuota == null || toQuota == null) {
            throw new RuntimeException("Tenant not found");
        }
        return tccTransferService.tryPhase(fromTenantId, toTenantId, granularity, amount);
    }

    public TransferTransaction transferQuotaConfirm(String transactionId) {
        return tccTransferService.confirmPhase(transactionId);
    }

    public TransferTransaction transferQuotaCancel(String transactionId) {
        return tccTransferService.cancelPhase(transactionId);
    }

    public TransferTransaction getTransferTransaction(String transactionId) {
        return tccTransferService.getTransaction(transactionId);
    }

    public PreConsumeResult preConsume(String tenantId, String granularity, long amount) {
        TenantQuota quota = getTenantQuota(tenantId);
        if (quota == null) {
            throw new RuntimeException("Tenant not found");
        }
        PreConsumeResult result = tokenBucketService.preConsumeWithDistributedLock(tenantId, granularity, amount);
        if (result.isSuccess()) {
            log.info("Pre-consumed {} quota for tenant {} (granularity: {}, newVersion: {})",
                    amount, tenantId, granularity, result.getNewVersion());
        } else {
            log.warn("Pre-consume failed for tenant {} (granularity: {}, reason: {})",
                    tenantId, granularity, result.getFailReason());
        }
        return result;
    }

    public boolean releasePreConsumed(String tenantId, String granularity, long amount) {
        boolean released = tokenBucketService.releasePreConsumedWithDistributedLock(tenantId, granularity, amount);
        if (released) {
            log.info("Released {} pre-consumed quota for tenant {} (granularity: {})",
                    amount, tenantId, granularity);
        }
        return released;
    }

    public boolean confirmPreConsumed(String tenantId, String granularity, long amount) {
        boolean confirmed = tokenBucketService.confirmPreConsumedWithDistributedLock(tenantId, granularity, amount);
        if (confirmed) {
            log.info("Confirmed {} pre-consumed quota for tenant {} (granularity: {})",
                    amount, tenantId, granularity);
        }
        return confirmed;
    }
}
