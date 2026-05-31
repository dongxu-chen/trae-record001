package com.datacheck.service;

import com.datacheck.check.CheckEngine;
import com.datacheck.model.CheckResult;
import com.datacheck.model.CheckTask;
import com.datacheck.model.GrayReleaseConfig;
import com.datacheck.model.GrayReleaseConfig.GrayPhase;
import com.datacheck.model.GrayReleaseConfig.GrayPhaseStatus;
import com.datacheck.model.GrayReleaseConfig.GrayStrategy;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class GrayReleaseService {

    private final CheckEngine checkEngine;

    private final Map<String, GrayReleaseConfig> grayConfigs = new ConcurrentHashMap<>();
    private final Cache<String, CheckResult> phaseResultCache = Caffeine.newBuilder()
            .expireAfterWrite(1, TimeUnit.HOURS)
            .maximumSize(50)
            .build();

    @Autowired
    public GrayReleaseService(CheckEngine checkEngine) {
        this.checkEngine = checkEngine;
    }

    public GrayReleaseConfig createGrayConfig(GrayReleaseConfig config) {
        if (config.getId() == null) {
            config.setId(UUID.randomUUID().toString());
        }
        config.setCreatedAt(LocalDateTime.now());
        config.setUpdatedAt(LocalDateTime.now());
        config.setCurrentPhase(0);

        if (config.getPhases() == null || config.getPhases().isEmpty()) {
            config.setPhases(buildDefaultPhases());
        }

        for (int i = 0; i < config.getPhases().size(); i++) {
            GrayPhase phase = config.getPhases().get(i);
            phase.setPhaseIndex(i);
            phase.setStatus(GrayPhaseStatus.PENDING);
        }

        grayConfigs.put(config.getId(), config);
        log.info("Created gray release config: {}, phases: {}", config.getId(), config.getPhases().size());
        return config;
    }

    private List<GrayPhase> buildDefaultPhases() {
        List<GrayPhase> phases = new ArrayList<>();
        phases.add(GrayPhase.builder()
                .phaseIndex(0).phaseName("灰度阶段1 - 10%").percentage(10)
                .durationMinutes(30).autoAdvance(true).status(GrayPhaseStatus.PENDING)
                .build());
        phases.add(GrayPhase.builder()
                .phaseIndex(1).phaseName("灰度阶段2 - 30%").percentage(30)
                .durationMinutes(30).autoAdvance(true).status(GrayPhaseStatus.PENDING)
                .build());
        phases.add(GrayPhase.builder()
                .phaseIndex(2).phaseName("灰度阶段3 - 60%").percentage(60)
                .durationMinutes(30).autoAdvance(true).status(GrayPhaseStatus.PENDING)
                .build());
        phases.add(GrayPhase.builder()
                .phaseIndex(3).phaseName("灰度阶段4 - 100%").percentage(100)
                .durationMinutes(0).autoAdvance(false).status(GrayPhaseStatus.PENDING)
                .build());
        return phases;
    }

    @Async("checkTaskExecutor")
    public void executeGrayCheck(String configId, CheckTask baseTask) {
        GrayReleaseConfig config = grayConfigs.get(configId);
        if (config == null || !config.isEnabled()) {
            log.warn("Gray config not found or disabled: {}", configId);
            return;
        }

        List<GrayPhase> phases = config.getPhases();
        for (int i = config.getCurrentPhase(); i < phases.size(); i++) {
            GrayPhase phase = phases.get(i);

            if (!config.isEnabled()) {
                log.info("Gray release paused at phase {}", i);
                phase.setStatus(GrayPhaseStatus.PAUSED);
                break;
            }

            phase.setStatus(GrayPhaseStatus.RUNNING);
            phase.setStartedAt(LocalDateTime.now());

            CheckTask phaseTask = buildPhaseTask(baseTask, config, phase);
            log.info("Starting gray phase {}: {}%, tables: {}",
                    phase.getPhaseIndex(), phase.getPercentage(), phase.getTableNames());

            try {
                checkEngine.executeCheck(phaseTask);

                Optional<CheckResult> resultOpt = checkEngine.getResult(phaseTask.getId());
                if (resultOpt.isPresent()) {
                    CheckResult result = resultOpt.get();
                    phase.setPhaseResult(result);
                    phaseResultCache.put(configId + "_phase_" + i, result);

                    if (result.getDiffCount() > 0 && shouldPauseForHighDiffRate(result)) {
                        log.warn("High diff rate detected in phase {}: {} diffs out of {} records, pausing gray release",
                                i, result.getDiffCount(), result.getTotalSourceRecords());
                        phase.setStatus(GrayPhaseStatus.FAILED);
                        config.setEnabled(false);
                        break;
                    }
                }

                phase.setStatus(GrayPhaseStatus.COMPLETED);
                phase.setCompletedAt(LocalDateTime.now());
                config.setCurrentPhase(i + 1);
                config.setUpdatedAt(LocalDateTime.now());

                log.info("Gray phase {} completed successfully", i);

                if (phase.isAutoAdvance() && phase.getDurationMinutes() > 0 && i < phases.size() - 1) {
                    log.info("Waiting {} minutes before advancing to next phase", phase.getDurationMinutes());
                    Thread.sleep(phase.getDurationMinutes() * 60 * 1000L);
                }

            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                phase.setStatus(GrayPhaseStatus.PAUSED);
                log.info("Gray release interrupted at phase {}", i);
                break;
            } catch (Exception e) {
                phase.setStatus(GrayPhaseStatus.FAILED);
                log.error("Gray phase {} failed", i, e);
                break;
            }
        }

        log.info("Gray release {} completed at phase {}", configId, config.getCurrentPhase());
    }

    private boolean shouldPauseForHighDiffRate(CheckResult result) {
        if (result.getTotalSourceRecords() == 0) return false;
        double diffRate = (double) result.getDiffCount() / result.getTotalSourceRecords();
        return diffRate > 0.1;
    }

    private CheckTask buildPhaseTask(CheckTask baseTask, GrayReleaseConfig config, GrayPhase phase) {
        CheckTask.CheckTaskBuilder builder = CheckTask.builder()
                .id(UUID.randomUUID().toString())
                .sourceType(baseTask.getSourceType())
                .tableName(baseTask.getTableName())
                .primaryKey(baseTask.getPrimaryKey())
                .compareFields(baseTask.getCompareFields())
                .excludeFields(baseTask.getExcludeFields())
                .autoRepair(baseTask.getAutoRepair())
                .stratifiedHashEnabled(baseTask.getStratifiedHashEnabled())
                .stratumCount(baseTask.getStratumCount())
                .importanceLevel(baseTask.getImportanceLevel())
                .status("PENDING")
                .createdAt(LocalDateTime.now());

        if (config.getStrategy() == GrayStrategy.TABLE_RANGE && phase.getTableNames() != null
                && !phase.getTableNames().isEmpty()) {
            builder.tableName(phase.getTableNames().get(0));
        }

        if (baseTask.getLatencyThresholdMs() != null) {
            builder.latencyThresholdMs(baseTask.getLatencyThresholdMs());
        }
        if (baseTask.getBatchSize() != null) {
            builder.batchSize(baseTask.getBatchSize());
        }

        return builder.build();
    }

    public GrayReleaseConfig advancePhase(String configId) {
        GrayReleaseConfig config = grayConfigs.get(configId);
        if (config == null) return null;

        List<GrayPhase> phases = config.getPhases();
        if (config.getCurrentPhase() < phases.size()) {
            GrayPhase currentPhase = phases.get(config.getCurrentPhase());
            if (currentPhase.getStatus() == GrayPhaseStatus.PAUSED ||
                    currentPhase.getStatus() == GrayPhaseStatus.PENDING) {
                config.setCurrentPhase(config.getCurrentPhase() + 1);
                config.setUpdatedAt(LocalDateTime.now());
                log.info("Manually advanced gray release {} to phase {}", configId, config.getCurrentPhase());
            }
        }
        return config;
    }

    public GrayReleaseConfig pauseGrayRelease(String configId) {
        GrayReleaseConfig config = grayConfigs.get(configId);
        if (config != null) {
            config.setEnabled(false);
            config.setUpdatedAt(LocalDateTime.now());
            log.info("Gray release {} paused", configId);
        }
        return config;
    }

    public GrayReleaseConfig resumeGrayRelease(String configId) {
        GrayReleaseConfig config = grayConfigs.get(configId);
        if (config != null) {
            config.setEnabled(true);
            config.setUpdatedAt(LocalDateTime.now());
            log.info("Gray release {} resumed", configId);
        }
        return config;
    }

    public Collection<GrayReleaseConfig> getAllGrayConfigs() {
        return grayConfigs.values();
    }

    public GrayReleaseConfig getGrayConfig(String configId) {
        return grayConfigs.get(configId);
    }
}
