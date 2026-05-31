package com.quota.management.service;

import com.quota.management.entity.QuotaUsage;
import com.quota.management.entity.TenantQuota;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class WarningService {

    private static final String WARNING_PREFIX = "quota:warning:";
    private static final String WARNING_LOG_PREFIX = "quota:warning-log:";

    public enum WarningLevel {
        EARLY_WARNING,
        WARNING,
        CRITICAL
    }

    private final QuotaManagementService quotaManagementService;
    private final RedisTemplate<String, Object> redisTemplate;

    @Value("${quota.warning.enabled:true}")
    private boolean warningEnabled;

    @Value("${quota.warning.early-threshold:0.6}")
    private double earlyThreshold;

    @Value("${quota.warning.threshold:0.8}")
    private double warningThreshold;

    @Value("${quota.warning.critical-threshold:0.95}")
    private double criticalThreshold;

    @Value("${quota.warning.cooldown-seconds:300}")
    private long cooldownSeconds;

    @Value("${quota.warning.early-cooldown-seconds:600}")
    private long earlyCooldownSeconds;

    public void checkAndSendWarning(String tenantId) {
        if (!warningEnabled) {
            return;
        }

        try {
            TenantQuota quota = quotaManagementService.getTenantQuota(tenantId);
            if (quota == null) {
                return;
            }

            QuotaUsage usage = quotaManagementService.getQuotaUsage(tenantId);
            double tenantThreshold = quota.getWarningThreshold() != null ? quota.getWarningThreshold() : warningThreshold;
            double tenantEarlyThreshold = Math.min(earlyThreshold, tenantThreshold - 0.15);

            List<GranularityWarning> warnings = new ArrayList<>();

            checkGranularity(warnings, "MINUTE", usage.getMinuteUsageRate(), tenantEarlyThreshold, tenantThreshold);
            checkGranularity(warnings, "HOUR", usage.getHourUsageRate(), tenantEarlyThreshold, tenantThreshold);
            checkGranularity(warnings, "DAY", usage.getDayUsageRate(), tenantEarlyThreshold, tenantThreshold);

            if (!warnings.isEmpty()) {
                for (GranularityWarning gw : warnings) {
                    sendWarning(tenantId, quota, usage, gw);
                }
            }

        } catch (Exception e) {
            log.error("Error checking warning for tenant: {}", tenantId, e);
        }
    }

    private void checkGranularity(List<GranularityWarning> warnings, String granularity,
                                  double usageRate, double earlyThreshold, double warningThreshold) {
        WarningLevel level = determineWarningLevel(usageRate, earlyThreshold, warningThreshold);
        if (level != null) {
            warnings.add(new GranularityWarning(granularity, level, usageRate));
        }
    }

    private WarningLevel determineWarningLevel(double usageRate, double earlyThreshold, double warningThreshold) {
        if (usageRate >= criticalThreshold) {
            return WarningLevel.CRITICAL;
        }
        if (usageRate >= warningThreshold) {
            return WarningLevel.WARNING;
        }
        if (usageRate >= earlyThreshold) {
            return WarningLevel.EARLY_WARNING;
        }
        return null;
    }

    private void sendWarning(String tenantId, TenantQuota quota, QuotaUsage usage, GranularityWarning gw) {
        String levelKey = WARNING_PREFIX + tenantId + ":" + gw.granularity + ":" + gw.level.name();
        Long lastWarning = (Long) redisTemplate.opsForValue().get(levelKey);
        long now = System.currentTimeMillis();

        long cooldown = gw.level == WarningLevel.EARLY_WARNING ? earlyCooldownSeconds : cooldownSeconds;
        long cooldownMs = cooldown * 1000;

        if (lastWarning != null && now - lastWarning < cooldownMs) {
            return;
        }

        WarningLog warningLog = WarningLog.builder()
                .tenantId(tenantId)
                .tenantName(quota.getTenantName())
                .granularity(gw.granularity)
                .warningLevel(gw.level.name())
                .usageRate(gw.usageRate)
                .earlyThreshold(earlyThreshold)
                .warningThreshold(warningThreshold)
                .criticalThreshold(criticalThreshold)
                .minuteUsageRate(usage.getMinuteUsageRate())
                .hourUsageRate(usage.getHourUsageRate())
                .dayUsageRate(usage.getDayUsageRate())
                .notificationEmail(quota.getNotificationEmail())
                .timestamp(LocalDateTime.now())
                .build();

        String logKey = WARNING_LOG_PREFIX + tenantId + ":" + gw.level.name() + ":" + now;
        redisTemplate.opsForValue().set(logKey, warningLog, 24, TimeUnit.HOURS);
        redisTemplate.opsForValue().set(levelKey, now, cooldown, TimeUnit.SECONDS);

        String levelDesc = getLevelDescription(gw.level);
        String colorCode = getLevelColorCode(gw.level);

        log.warn("QUOTA {} [{}]: Tenant={}, Name={}, Granularity={}, Usage={}%, " +
                        "Thresholds=[early={}%, warn={}%, critical={}%]",
                levelDesc, colorCode,
                tenantId, quota.getTenantName(), gw.granularity,
                String.format("%.1f", gw.usageRate * 100),
                String.format("%.0f", earlyThreshold * 100),
                String.format("%.0f", warningThreshold * 100),
                String.format("%.0f", criticalThreshold * 100));

        if (quota.getNotificationEmail() != null) {
            log.info("Would send {} warning email to: {} for tenant: {} ({})",
                    levelDesc, quota.getNotificationEmail(), tenantId, gw.granularity);
        }

        if (gw.level == WarningLevel.CRITICAL) {
            log.error("CRITICAL: Tenant {} has exceeded {}% on {} granularity! Immediate action required.",
                    tenantId, String.format("%.1f", gw.usageRate * 100), gw.granularity);
        }
    }

    private String getLevelDescription(WarningLevel level) {
        switch (level) {
            case EARLY_WARNING:
                return "EARLY-WARNING";
            case WARNING:
                return "WARNING";
            case CRITICAL:
                return "CRITICAL";
            default:
                return "UNKNOWN";
        }
    }

    private String getLevelColorCode(WarningLevel level) {
        switch (level) {
            case EARLY_WARNING:
                return "YELLOW";
            case WARNING:
                return "ORANGE";
            case CRITICAL:
                return "RED";
            default:
                return "WHITE";
        }
    }

    public List<WarningLog> getRecentWarnings(String tenantId) {
        List<WarningLog> warnings = new ArrayList<>();
        Set<String> keys = redisTemplate.keys(WARNING_LOG_PREFIX + tenantId + ":*");
        if (keys != null) {
            for (String key : keys) {
                Object obj = redisTemplate.opsForValue().get(key);
                if (obj instanceof WarningLog) {
                    warnings.add((WarningLog) obj);
                }
            }
        }
        warnings.sort((a, b) -> b.getTimestamp().compareTo(a.getTimestamp()));
        return warnings;
    }

    @Scheduled(fixedRate = 30000)
    public void checkAllTenantsWarnings() {
        if (!warningEnabled) {
            return;
        }

        List<TenantQuota> tenants = quotaManagementService.getAllTenantQuotas();
        for (TenantQuota tenant : tenants) {
            checkAndSendWarning(tenant.getTenantId());
        }
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class WarningLog implements java.io.Serializable {
        private String tenantId;
        private String tenantName;
        private String granularity;
        private String warningLevel;
        private double usageRate;
        private double earlyThreshold;
        private double warningThreshold;
        private double criticalThreshold;
        private double minuteUsageRate;
        private double hourUsageRate;
        private double dayUsageRate;
        private String notificationEmail;
        private LocalDateTime timestamp;
    }

    @lombok.Data
    @lombok.AllArgsConstructor
    private static class GranularityWarning {
        private String granularity;
        private WarningLevel level;
        private double usageRate;
    }
}
