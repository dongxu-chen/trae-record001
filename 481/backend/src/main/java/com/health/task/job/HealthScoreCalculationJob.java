package com.health.task.job;

import com.health.task.service.HealthScoringService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class HealthScoreCalculationJob implements Job {

    private final HealthScoringService scoringService;

    @Override
    public void execute(JobExecutionContext context) {
        log.info("Starting periodic health score calculation...");
        try {
            scoringService.calculateAndSaveAllScores();
            log.info("Health score calculation completed successfully");
        } catch (Exception e) {
            log.error("Health score calculation failed", e);
        }
    }
}
