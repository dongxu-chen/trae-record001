package com.replay.detector.scheduler;

import com.replay.detector.config.ReplayDetectionProperties;
import com.replay.detector.service.AdaptiveThresholdService;
import com.replay.detector.service.BloomFilterService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class SystemMaintenanceScheduler {

    private final BloomFilterService bloomFilterService;
    private final AdaptiveThresholdService adaptiveThresholdService;
    private final ReplayDetectionProperties properties;

    @Scheduled(fixedRate = 300000)
    public void cleanupExpiredDistributedFilter() {
        log.debug("Running bloom filter cleanup task");
        bloomFilterService.cleanupDistributedExpired();
    }

    @Scheduled(fixedRate = 30000)
    public void refreshAdaptiveThreshold() {
        if (!properties.getAdaptive().isEnabled()) {
            return;
        }
        log.debug("Refreshing adaptive threshold state");
        adaptiveThresholdService.refreshState();
    }
}
