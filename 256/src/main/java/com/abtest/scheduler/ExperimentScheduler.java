package com.abtest.scheduler;

import com.abtest.entity.Experiment;
import com.abtest.repository.ExperimentRepository;
import com.abtest.service.AutoStopService;
import com.abtest.service.MABService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class ExperimentScheduler {

    private final ExperimentRepository experimentRepository;
    private final MABService mabService;
    private final AutoStopService autoStopService;

    @Scheduled(fixedDelayString = "${abtest.scheduler.mab-interval-minutes:30}")
    public void updateMABTrafficAllocations() {
        log.debug("Starting MAB traffic allocation update...");

        List<Experiment> runningExperiments = experimentRepository
            .findByStatus(Experiment.ExperimentStatus.RUNNING);

        int updatedCount = 0;
        for (Experiment experiment : runningExperiments) {
            if (experiment.getTrafficMode() != Experiment.TrafficAllocationMode.FIXED
                && mabService.shouldUpdateTraffic(experiment)) {
                try {
                    mabService.updateTrafficAllocation(experiment.getId());
                    updatedCount++;
                } catch (Exception e) {
                    log.error("Failed to update MAB traffic for experiment: {}",
                        experiment.getId(), e);
                }
            }
        }

        if (updatedCount > 0) {
            log.info("Updated MAB traffic allocation for {} experiments", updatedCount);
        }
    }

    @Scheduled(fixedDelayString = "${abtest.scheduler.autostop-interval-minutes:60}")
    public void checkAutoStopConditions() {
        log.debug("Starting auto-stop condition check...");

        List<Experiment> runningExperiments = experimentRepository
            .findByStatus(Experiment.ExperimentStatus.RUNNING);

        int stoppedCount = 0;
        for (Experiment experiment : runningExperiments) {
            if (Boolean.TRUE.equals(experiment.getAutoStopEnabled())) {
                try {
                    AutoStopService.AutoStopCheckResult result = autoStopService
                        .checkAndStopIfNeeded(experiment.getId());
                    if (result.shouldStop()) {
                        stoppedCount++;
                        log.info("Experiment {} automatically stopped: {}",
                            experiment.getId(), result.getStopReason());
                    }
                } catch (Exception e) {
                    log.error("Failed to check auto-stop for experiment: {}",
                        experiment.getId(), e);
                }
            }
        }

        if (stoppedCount > 0) {
            log.info("Automatically stopped {} experiments", stoppedCount);
        }
    }
}
