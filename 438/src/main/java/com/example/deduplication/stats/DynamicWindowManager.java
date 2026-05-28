package com.example.deduplication.stats;

import com.example.deduplication.config.DeduplicationProperties;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class DynamicWindowManager {

    private final DeduplicationProperties properties;
    private final QpsStatisticsService qpsService;

    private volatile long currentWindowSeconds;
    private volatile long lastAdjustmentTime;

    @PostConstruct
    public void init() {
        DeduplicationProperties.DynamicWindowConfig config = properties.getDynamicWindow();
        this.currentWindowSeconds = config.getDefaultWindowSeconds();
        this.lastAdjustmentTime = System.currentTimeMillis();
        log.info("Dynamic Window Manager initialized - current window: {}s", currentWindowSeconds);
    }

    public long getCurrentWindowSeconds() {
        if (!properties.getDynamicWindow().isEnabled()) {
            return properties.getWindowSeconds();
        }
        return currentWindowSeconds;
    }

    @Scheduled(fixedRate = 5000)
    public void adjustWindowSize() {
        if (!properties.getDynamicWindow().isEnabled()) {
            return;
        }

        DeduplicationProperties.DynamicWindowConfig config = properties.getDynamicWindow();
        double currentQps = qpsService.getCurrentQps();

        long newWindowSeconds = calculateNewWindowSize(currentQps, config);

        if (newWindowSeconds != currentWindowSeconds) {
            log.info("Adjusting window size: {}s -> {}s (QPS: {:.2f})",
                    currentWindowSeconds, newWindowSeconds, currentQps);
            currentWindowSeconds = newWindowSeconds;
            lastAdjustmentTime = System.currentTimeMillis();
        }
    }

    private long calculateNewWindowSize(double currentQps,
                                        DeduplicationProperties.DynamicWindowConfig config) {
        long minWindow = config.getMinWindowSeconds();
        long maxWindow = config.getMaxWindowSeconds();
        long highThreshold = config.getQpsThresholdHigh();
        long lowThreshold = config.getQpsThresholdLow();
        int factor = config.getAdjustmentFactor();

        long newWindow = currentWindowSeconds;

        if (currentQps > highThreshold) {
            newWindow = Math.min(currentWindowSeconds * factor, maxWindow);
            log.debug("High QPS detected ({} > {}), expanding window", currentQps, highThreshold);
        } else if (currentQps < lowThreshold) {
            newWindow = Math.max(currentWindowSeconds / factor, minWindow);
            log.debug("Low QPS detected ({} < {}), shrinking window", currentQps, lowThreshold);
        }

        return newWindow;
    }

    public WindowStats getWindowStats() {
        return WindowStats.builder()
                .currentWindowSeconds(currentWindowSeconds)
                .currentQps(qpsService.getCurrentQps())
                .lastAdjustmentTime(lastAdjustmentTime)
                .minWindowSeconds(properties.getDynamicWindow().getMinWindowSeconds())
                .maxWindowSeconds(properties.getDynamicWindow().getMaxWindowSeconds())
                .build();
    }

    @lombok.Data
    @lombok.Builder
    public static class WindowStats {
        private long currentWindowSeconds;
        private double currentQps;
        private long lastAdjustmentTime;
        private long minWindowSeconds;
        private long maxWindowSeconds;
    }
}
