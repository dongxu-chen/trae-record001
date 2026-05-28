package com.ratelimit.center.service;

import com.alibaba.csp.sentinel.slots.block.flow.FlowRule;
import com.alibaba.csp.sentinel.slots.block.flow.FlowRuleManager;
import com.alibaba.fastjson.JSON;
import com.ratelimit.center.common.RateLimitConstants;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import oshi.SystemInfo;
import oshi.hardware.CentralProcessor;
import oshi.hardware.GlobalMemory;

import javax.annotation.PostConstruct;
import java.lang.management.ManagementFactory;
import java.lang.management.OperatingSystemMXBean;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class AdaptiveRateLimitService {

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @Value("${rate-limit.adaptive.enabled:true}")
    private boolean adaptiveEnabled;

    @Value("${rate-limit.adaptive.adjust-interval-seconds:60}")
    private int adjustIntervalSeconds;

    @Value("${rate-limit.adaptive.cpu-threshold-high:80}")
    private double cpuThresholdHigh;

    @Value("${rate-limit.adaptive.cpu-threshold-low:50}")
    private double cpuThresholdLow;

    @Value("${rate-limit.adaptive.mem-threshold-high:85}")
    private double memThresholdHigh;

    @Value("${rate-limit.adaptive.mem-threshold-low:60}")
    private double memThresholdLow;

    @Value("${rate-limit.adaptive.rt-threshold-ms:1000}")
    private double rtThresholdMs;

    @Value("${rate-limit.adaptive.max-decrease-percent:50}")
    private double maxDecreasePercent;

    @Value("${rate-limit.adaptive.max-increase-percent:30}")
    private double maxIncreasePercent;

    private final Map<String, AdaptiveRuleConfig> adaptiveRuleMap = new ConcurrentHashMap<>();

    private final SystemInfo systemInfo = new SystemInfo();

    private final Map<String, Double> originalThresholdMap = new ConcurrentHashMap<>();

    @Data
    public static class AdaptiveRuleConfig {
        private String resource;
        private double baseThreshold;
        private double currentThreshold;
        private int adjustDirection;
        private int adjustCount;
        private String adjustReason;
        private long lastAdjustTime;
        private boolean enabled;
        private String strategy;
        private double minThreshold;
        private double maxThreshold;

        public double calculateNewThreshold(SystemLoad load) {
            double newThreshold = currentThreshold;

            if ("cpu".equals(strategy)) {
                if (load.cpuUsage > cpuThresholdHigh) {
                    newThreshold = currentThreshold * (1 - (load.cpuUsage - cpuThresholdHigh) / 100 * 0.5);
                } else if (load.cpuUsage < cpuThresholdLow) {
                    newThreshold = currentThreshold * (1 + (cpuThresholdLow - load.cpuUsage) / 100 * 0.3);
                }
            } else if ("mem".equals(strategy)) {
                if (load.memUsage > memThresholdHigh) {
                    newThreshold = currentThreshold * (1 - (load.memUsage - memThresholdHigh) / 100 * 0.5);
                } else if (load.memUsage < memThresholdLow) {
                    newThreshold = currentThreshold * (1 + (memThresholdLow - load.memUsage) / 100 * 0.3);
                }
            } else {
                double score = calculateLoadScore(load);
                if (score > 0.8) {
                    double decreaseRate = Math.min(maxDecreasePercent / 100, (score - 0.8) * 2);
                    newThreshold = currentThreshold * (1 - decreaseRate);
                } else if (score < 0.4) {
                    double increaseRate = Math.min(maxIncreasePercent / 100, (0.4 - score) * 2);
                    newThreshold = currentThreshold * (1 + increaseRate);
                }
            }

            newThreshold = Math.max(minThreshold, Math.min(maxThreshold, newThreshold));
            return newThreshold;
        }

        private double calculateLoadScore(SystemLoad load) {
            double score = 0;
            score += load.cpuUsage / 100 * 0.35;
            score += load.memUsage / 100 * 0.35;
            if (load.avgRt > 0) {
                score += Math.min(1.0, load.avgRt / rtThresholdMs) * 0.20;
            }
            score += Math.min(1.0, load.blockRate) * 0.10;
            return score;
        }
    }

    @Data
    public static class SystemLoad {
        private double cpuUsage;
        private double memUsage;
        private double loadAverage;
        private double avgRt;
        private double blockRate;
        private long timestamp;

        public boolean isOverloaded() {
            return cpuUsage > 80 || memUsage > 85 || blockRate > 0.1;
        }
    }

    @Data
    public static class AdjustHistory {
        private String resource;
        private double oldThreshold;
        private double newThreshold;
        private String reason;
        private double cpuUsage;
        private double memUsage;
        private long timestamp;
    }

    private final List<AdjustHistory> adjustHistoryList = Collections.synchronizedList(new ArrayList<>());

    @PostConstruct
    public void init() {
        if (!adaptiveEnabled) {
            log.info("Adaptive rate limit is disabled");
            return;
        }
        log.info("Adaptive rate limit initialized, adjust interval: {}s", adjustIntervalSeconds);
    }

    public SystemLoad getCurrentSystemLoad() {
        SystemLoad load = new SystemLoad();
        try {
            CentralProcessor processor = systemInfo.getHardware().getProcessor();
            long[] prevTicks = processor.getSystemCpuLoadTicks();
            try {
                Thread.sleep(500);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            long[] ticks = processor.getSystemCpuLoadTicks();
            long user = ticks[CentralProcessor.TickType.USER.getIndex()] - prevTicks[CentralProcessor.TickType.USER.getIndex()];
            long nice = ticks[CentralProcessor.TickType.NICE.getIndex()] - prevTicks[CentralProcessor.TickType.NICE.getIndex()];
            long sys = ticks[CentralProcessor.TickType.SYSTEM.getIndex()] - prevTicks[CentralProcessor.TickType.SYSTEM.getIndex()];
            long idle = ticks[CentralProcessor.TickType.IDLE.getIndex()] - prevTicks[CentralProcessor.TickType.IDLE.getIndex()];
            long total = user + nice + sys + idle;
            load.setCpuUsage(total > 0 ? (100.0 * (user + nice + sys) / total) : 0);

            GlobalMemory memory = systemInfo.getHardware().getMemory();
            long totalMem = memory.getTotal();
            long availableMem = memory.getAvailable();
            load.setMemUsage(totalMem > 0 ? (100.0 * (totalMem - availableMem) / totalMem) : 0);

            OperatingSystemMXBean osBean = ManagementFactory.getOperatingSystemMXBean();
            load.setLoadAverage(osBean.getSystemLoadAverage());
            load.setTimestamp(System.currentTimeMillis());

        } catch (Exception e) {
            log.warn("Failed to get system load", e);
        }
        return load;
    }

    public void registerAdaptiveRule(String resource, double baseThreshold, String strategy) {
        AdaptiveRuleConfig config = new AdaptiveRuleConfig();
        config.setResource(resource);
        config.setBaseThreshold(baseThreshold);
        config.setCurrentThreshold(baseThreshold);
        config.setEnabled(true);
        config.setStrategy(strategy != null ? strategy : "auto");
        config.setMinThreshold(baseThreshold * 0.3);
        config.setMaxThreshold(baseThreshold * 2.0);
        config.setLastAdjustTime(System.currentTimeMillis());

        originalThresholdMap.put(resource, baseThreshold);
        adaptiveRuleMap.put(resource, config);

        log.info("Registered adaptive rule for resource: {}, base threshold: {}, strategy: {}",
                resource, baseThreshold, strategy);
    }

    public void unregisterAdaptiveRule(String resource) {
        AdaptiveRuleConfig config = adaptiveRuleMap.remove(resource);
        if (config != null) {
            restoreOriginalThreshold(resource);
            log.info("Unregistered adaptive rule for resource: {}", resource);
        }
    }

    private void restoreOriginalThreshold(String resource) {
        Double original = originalThresholdMap.get(resource);
        if (original != null) {
            updateFlowRuleThreshold(resource, original);
        }
    }

    private void updateFlowRuleThreshold(String resource, double threshold) {
        List<FlowRule> rules = FlowRuleManager.getRules();
        for (FlowRule rule : rules) {
            if (resource.equals(rule.getResource())) {
                rule.setCount(threshold);
                FlowRuleManager.loadRules(rules);
                break;
            }
        }
    }

    @Scheduled(fixedDelayString = "${rate-limit.adaptive.adjust-interval-seconds:60}000")
    public void adjustThresholds() {
        if (!adaptiveEnabled || adaptiveRuleMap.isEmpty()) {
            return;
        }

        try {
            SystemLoad load = getCurrentSystemLoad();
            log.debug("System load - CPU: {}%, MEM: {}%, LoadAvg: {}",
                    String.format("%.1f", load.getCpuUsage()),
                    String.format("%.1f", load.getMemUsage()),
                    load.getLoadAverage());

            for (Map.Entry<String, AdaptiveRuleConfig> entry : adaptiveRuleMap.entrySet()) {
                adjustRuleThreshold(entry.getKey(), entry.getValue(), load);
            }

            saveSystemLoadToRedis(load);

        } catch (Exception e) {
            log.error("Failed to adjust thresholds", e);
        }
    }

    private void adjustRuleThreshold(String resource, AdaptiveRuleConfig config, SystemLoad load) {
        if (!config.isEnabled()) {
            return;
        }

        double oldThreshold = config.getCurrentThreshold();
        double newThreshold = config.calculateNewThreshold(load);

        if (Math.abs(newThreshold - oldThreshold) > oldThreshold * 0.01) {
            config.setCurrentThreshold(newThreshold);
            config.setLastAdjustTime(System.currentTimeMillis());
            config.setAdjustCount(config.getAdjustCount() + 1);

            String reason = generateAdjustReason(load);
            config.setAdjustReason(reason);

            updateFlowRuleThreshold(resource, newThreshold);

            AdjustHistory history = new AdjustHistory();
            history.setResource(resource);
            history.setOldThreshold(oldThreshold);
            history.setNewThreshold(newThreshold);
            history.setReason(reason);
            history.setCpuUsage(load.getCpuUsage());
            history.setMemUsage(load.getMemUsage());
            history.setTimestamp(System.currentTimeMillis());
            addAdjustHistory(history);

            log.info("Adjusted threshold for resource: {}: {} -> {}, reason: {}",
                    resource,
                    String.format("%.2f", oldThreshold),
                    String.format("%.2f", newThreshold),
                    reason);
        }
    }

    private String generateAdjustReason(SystemLoad load) {
        List<String> reasons = new ArrayList<>();
        if (load.getCpuUsage() > cpuThresholdHigh) {
            reasons.add("CPU_HIGH(" + (int) load.getCpuUsage() + "%)");
        } else if (load.getCpuUsage() < cpuThresholdLow) {
            reasons.add("CPU_LOW(" + (int) load.getCpuUsage() + "%)");
        }
        if (load.getMemUsage() > memThresholdHigh) {
            reasons.add("MEM_HIGH(" + (int) load.getMemUsage() + "%)");
        } else if (load.getMemUsage() < memThresholdLow) {
            reasons.add("MEM_LOW(" + (int) load.getMemUsage() + "%)");
        }
        if (reasons.isEmpty()) {
            reasons.add("NORMAL");
        }
        return String.join(",", reasons);
    }

    private void addAdjustHistory(AdjustHistory history) {
        adjustHistoryList.add(0, history);
        if (adjustHistoryList.size() > 1000) {
            adjustHistoryList.remove(adjustHistoryList.size() - 1);
        }
    }

    private void saveSystemLoadToRedis(SystemLoad load) {
        try {
            String key = RateLimitConstants.REDIS_KEY_PREFIX + "system:load:latest";
            stringRedisTemplate.opsForValue().set(key, JSON.toJSONString(load), 5, TimeUnit.MINUTES);
        } catch (Exception e) {
            log.warn("Failed to save system load to Redis", e);
        }
    }

    public Map<String, AdaptiveRuleConfig> getAllAdaptiveRules() {
        return new ConcurrentHashMap<>(adaptiveRuleMap);
    }

    public AdaptiveRuleConfig getAdaptiveRule(String resource) {
        return adaptiveRuleMap.get(resource);
    }

    public List<AdjustHistory> getAdjustHistory(String resource, int limit) {
        List<AdjustHistory> result = new ArrayList<>();
        for (AdjustHistory history : adjustHistoryList) {
            if (resource == null || resource.equals(history.getResource())) {
                result.add(history);
                if (result.size() >= limit) {
                    break;
                }
            }
        }
        return result;
    }

    public void updateAdaptiveRuleConfig(String resource, double minThreshold, double maxThreshold, String strategy) {
        AdaptiveRuleConfig config = adaptiveRuleMap.get(resource);
        if (config != null) {
            config.setMinThreshold(minThreshold);
            config.setMaxThreshold(maxThreshold);
            if (strategy != null) {
                config.setStrategy(strategy);
            }
        }
    }

    public void toggleAdaptiveRule(String resource, boolean enabled) {
        AdaptiveRuleConfig config = adaptiveRuleMap.get(resource);
        if (config != null) {
            config.setEnabled(enabled);
            if (!enabled) {
                restoreOriginalThreshold(resource);
            }
        }
    }

    public Map<String, Object> getAdaptiveStatus() {
        Map<String, Object> status = new LinkedHashMap<>();
        status.put("enabled", adaptiveEnabled);
        status.put("adjustIntervalSeconds", adjustIntervalSeconds);
        status.put("systemLoad", getCurrentSystemLoad());
        status.put("adaptiveRuleCount", adaptiveRuleMap.size());
        status.put("adjustHistoryCount", adjustHistoryList.size());
        status.put("cpuThresholdHigh", cpuThresholdHigh);
        status.put("cpuThresholdLow", cpuThresholdLow);
        status.put("memThresholdHigh", memThresholdHigh);
        status.put("memThresholdLow", memThresholdLow);
        return status;
    }
}
