package com.grayrelease.release.service;

import com.grayrelease.common.enums.MetricType;
import com.grayrelease.common.model.Experiment;
import com.grayrelease.common.model.MetricThreshold;
import com.grayrelease.monitor.service.AnomalyDetectionService;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
@RequiredArgsConstructor
public class QualityGateService {

    private final AnomalyDetectionService anomalyDetectionService;

    @Value("${quality-gate.min-observation-minutes:5}")
    private int minObservationMinutes;

    @Value("${quality-gate.auto-progress-enabled:true}")
    private boolean autoProgressEnabled;

    private final Map<String, GateCheckContext> gateContexts = new ConcurrentHashMap<>();

    private final Map<String, Experiment> monitoredExperiments = new ConcurrentHashMap<>();

    public void registerExperiment(Experiment experiment) {
        GateCheckContext context = new GateCheckContext();
        context.setExperimentId(experiment.getId());
        context.setServiceName(experiment.getServiceName());
        context.setVersion(experiment.getExperimentVersion());
        context.setSuccessMetrics(experiment.getSuccessMetrics());
        context.setGuardrailMetrics(experiment.getGuardrailMetrics());
        context.setObservationStartTime(LocalDateTime.now());
        context.setStepTrafficPercents(experiment.getStepTrafficPercents());
        context.setCurrentStep(experiment.getCurrentStep());
        context.setMaxTrafficPercent(experiment.getMaxTrafficPercent());
        context.setCheckCount(0);
        context.setPassCount(0);

        gateContexts.put(experiment.getId(), context);
        monitoredExperiments.put(experiment.getId(), experiment);

        log.info("Quality gate registered for experiment: id={}, name={}",
                experiment.getId(), experiment.getName());
    }

    public void unregisterExperiment(String experimentId) {
        gateContexts.remove(experimentId);
        monitoredExperiments.remove(experimentId);
        log.info("Quality gate unregistered for experiment: {}", experimentId);
    }

    @Scheduled(fixedRate = 30000)
    public void checkQualityGates() {
        if (!autoProgressEnabled) {
            return;
        }

        for (Map.Entry<String, GateCheckContext> entry : gateContexts.entrySet()) {
            String experimentId = entry.getKey();
            GateCheckContext context = entry.getValue();

            try {
                checkAndProgress(experimentId, context);
            } catch (Exception e) {
                log.error("Error checking quality gate for experiment: {}", experimentId, e);
            }
        }
    }

    private void checkAndProgress(String experimentId, GateCheckContext context) {
        long observationMinutes = java.time.Duration.between(
                context.getObservationStartTime(), LocalDateTime.now()).toMinutes();

        if (observationMinutes < minObservationMinutes) {
            log.debug("Skipping quality gate check: observation time {}min < {}min",
                    observationMinutes, minObservationMinutes);
            return;
        }

        GateResult successResult = checkMetrics(context.getServiceName(),
                context.getVersion(), context.getSuccessMetrics());

        GateResult guardrailResult = checkMetrics(context.getServiceName(),
                context.getVersion(), context.getGuardrailMetrics());

        context.setCheckCount(context.getCheckCount() + 1);

        if (!guardrailResult.isPassed()) {
            log.warn("Guardrail metrics failed for experiment: {}, rolling back", experimentId);
            triggerRollback(experimentId, "Guardrail failed: " + guardrailResult.getFailedMetrics());
            return;
        }

        if (successResult.isPassed()) {
            context.setPassCount(context.getPassCount() + 1);

            if (context.getPassCount() >= 3) {
                log.info("Quality gate passed for experiment: {}, pass count={}",
                        experimentId, context.getPassCount());

                if (context.getCurrentStep() < context.getStepTrafficPercents().size() - 1) {
                    int nextStep = context.getCurrentStep() + 1;
                    int nextPercent = Math.min(
                            context.getStepTrafficPercents().get(nextStep),
                            context.getMaxTrafficPercent()
                    );

                    if (nextPercent > context.getCurrentTrafficPercent()) {
                        log.info("Auto-progressing experiment: {} to step {}, traffic {}%",
                                experimentId, nextStep, nextPercent);

                        context.setCurrentStep(nextStep);
                        context.setCurrentTrafficPercent(nextPercent);
                        context.setObservationStartTime(LocalDateTime.now());
                        context.setPassCount(0);
                        context.setCheckCount(0);

                        updateExperimentTraffic(experimentId, nextStep);
                    }
                }
            }
        } else {
            context.setPassCount(0);
            log.debug("Quality gate not passed: experiment={}, pass count reset", experimentId);
        }
    }

    private GateResult checkMetrics(String serviceName, String version, List<MetricThreshold> thresholds) {
        GateResult result = new GateResult();
        result.setPassed(true);

        if (thresholds == null || thresholds.isEmpty()) {
            return result;
        }

        for (MetricThreshold threshold : thresholds) {
            com.grayrelease.common.dto.MetricData metricData =
                    anomalyDetectionService.checkMetric(serviceName, version, threshold.getMetricType(), threshold);

            if (metricData != null && metricData.getIsAbnormal()) {
                result.setPassed(false);
                result.getFailedMetrics().add(threshold.getMetricType().name() + "=" + metricData.getValue());
            }
        }

        return result;
    }

    private void updateExperimentTraffic(String experimentId, int step) {
        Experiment experiment = monitoredExperiments.get(experimentId);
        if (experiment != null) {
            experiment.setCurrentStep(step);
            if (step < experiment.getStepTrafficPercents().size()) {
                experiment.setCurrentTrafficPercent(
                        Math.min(experiment.getStepTrafficPercents().get(step),
                                experiment.getMaxTrafficPercent())
                );
            }
        }
    }

    private void triggerRollback(String experimentId, String reason) {
        log.warn("Quality gate triggered rollback: experiment={}, reason={}", experimentId, reason);
        unregisterExperiment(experimentId);
    }

    public GateStatus getGateStatus(String experimentId) {
        GateCheckContext context = gateContexts.get(experimentId);
        if (context == null) {
            return null;
        }

        GateStatus status = new GateStatus();
        status.setExperimentId(experimentId);
        status.setCheckCount(context.getCheckCount());
        status.setPassCount(context.getPassCount());
        status.setCurrentStep(context.getCurrentStep());
        status.setCurrentTrafficPercent(context.getCurrentTrafficPercent());
        status.setObservationMinutes(java.time.Duration.between(
                context.getObservationStartTime(), LocalDateTime.now()).toMinutes());
        status.setMinObservationMinutes(minObservationMinutes);
        status.setAutoProgressEnabled(autoProgressEnabled);

        return status;
    }

    public Map<String, GateStatus> getAllGateStatuses() {
        Map<String, GateStatus> statuses = new HashMap<>();
        for (String experimentId : gateContexts.keySet()) {
            GateStatus status = getGateStatus(experimentId);
            if (status != null) {
                statuses.put(experimentId, status);
            }
        }
        return statuses;
    }

    @Data
    public static class GateCheckContext {
        private String experimentId;
        private String serviceName;
        private String version;
        private List<MetricThreshold> successMetrics;
        private List<MetricThreshold> guardrailMetrics;
        private LocalDateTime observationStartTime;
        private List<Integer> stepTrafficPercents;
        private int currentStep;
        private int currentTrafficPercent;
        private int maxTrafficPercent;
        private int checkCount;
        private int passCount;
    }

    @Data
    public static class GateResult {
        private boolean passed;
        private List<String> failedMetrics = new ArrayList<>();
    }

    @Data
    public static class GateStatus {
        private String experimentId;
        private int checkCount;
        private int passCount;
        private int currentStep;
        private int currentTrafficPercent;
        private long observationMinutes;
        private int minObservationMinutes;
        private boolean autoProgressEnabled;
    }
}