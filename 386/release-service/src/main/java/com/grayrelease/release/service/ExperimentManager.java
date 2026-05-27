package com.grayrelease.release.service;

import com.grayrelease.common.dto.ExperimentRequest;
import com.grayrelease.common.dto.ExperimentResponse;
import com.grayrelease.common.enums.ExperimentStatus;
import com.grayrelease.common.model.Experiment;
import com.grayrelease.common.model.MetricThreshold;
import com.grayrelease.common.util.IdGenerator;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class ExperimentManager {

    private final Map<String, Experiment> experimentStore = new ConcurrentHashMap<>();

    private final Map<String, List<Experiment>> groupExperiments = new ConcurrentHashMap<>();

    private final ReleaseService releaseService;

    private final QualityGateService qualityGateService;

    public ExperimentResponse createExperiment(ExperimentRequest request) {
        log.info("Creating experiment: name={}, service={}, group={}",
                request.getName(), request.getServiceName(), request.getExperimentGroup());

        String experimentId = IdGenerator.generateId();

        List<Integer> stepPercents = request.getStepTrafficPercents();
        if (stepPercents == null || stepPercents.isEmpty()) {
            stepPercents = List.of(5, 10, 25, 50);
        }

        int maxTraffic = request.getMaxTrafficPercent() > 0 ? request.getMaxTrafficPercent() : 50;

        Experiment experiment = Experiment.builder()
                .id(experimentId)
                .name(request.getName())
                .description(request.getDescription())
                .serviceName(request.getServiceName())
                .experimentGroup(request.getExperimentGroup())
                .strategy(request.getStrategy())
                .status(ExperimentStatus.DRAFT)
                .stableVersion(request.getStableVersion())
                .experimentVersion(request.getExperimentVersion())
                .experimentImage(request.getExperimentImage())
                .maxTrafficPercent(maxTraffic)
                .currentTrafficPercent(0)
                .stepTrafficPercents(stepPercents)
                .currentStep(-1)
                .trafficMatchRules(request.getTrafficMatchRules())
                .successMetrics(request.getSuccessMetrics())
                .guardrailMetrics(request.getGuardrailMetrics())
                .startTime(request.getStartTime() != null ? request.getStartTime() : LocalDateTime.now())
                .endTime(request.getEndTime())
                .owner(request.getOwner())
                .metadata(request.getMetadata())
                .build();

        experimentStore.put(experimentId, experiment);

        String groupKey = getGroupKey(request.getServiceName(), request.getExperimentGroup());
        groupExperiments.computeIfAbsent(groupKey, k -> new ArrayList<>()).add(experiment);

        log.info("Experiment created: id={}, name={}", experimentId, request.getName());
        return buildResponse(experiment, "Experiment created successfully");
    }

    public ExperimentResponse startExperiment(String experimentId) {
        Experiment experiment = experimentStore.get(experimentId);
        if (experiment == null) {
            return ExperimentResponse.builder()
                    .experimentId(experimentId)
                    .status(ExperimentStatus.CANCELLED)
                    .message("Experiment not found")
                    .build();
        }

        if (!checkConflict(experiment)) {
            return ExperimentResponse.builder()
                    .experimentId(experimentId)
                    .status(ExperimentStatus.DRAFT)
                    .message("Conflict: another experiment is running for the same service")
                    .build();
        }

        experiment.setStatus(ExperimentStatus.RUNNING);
        experiment.setCurrentStep(0);
        experiment.setCurrentTrafficPercent(experiment.getStepTrafficPercents().get(0));
        experiment.setStartTime(LocalDateTime.now());

        qualityGateService.registerExperiment(experiment);

        applyTraffic(experiment);

        log.info("Experiment started: id={}, name={}, traffic={}%",
                experimentId, experiment.getName(), experiment.getCurrentTrafficPercent());
        return buildResponse(experiment, "Experiment started");
    }

    public ExperimentResponse progressExperiment(String experimentId, int step) {
        Experiment experiment = experimentStore.get(experimentId);
        if (experiment == null) {
            return ExperimentResponse.builder()
                    .experimentId(experimentId)
                    .status(ExperimentStatus.CANCELLED)
                    .message("Experiment not found")
                    .build();
        }

        if (experiment.getStatus() != ExperimentStatus.RUNNING) {
            return buildResponse(experiment, "Experiment is not running");
        }

        List<Integer> steps = experiment.getStepTrafficPercents();
        if (step >= steps.size()) {
            return completeExperiment(experimentId);
        }

        int newPercent = Math.min(steps.get(step), experiment.getMaxTrafficPercent());
        experiment.setCurrentStep(step);
        experiment.setCurrentTrafficPercent(newPercent);

        applyTraffic(experiment);

        log.info("Experiment progressed: id={}, step={}, traffic={}%", experimentId, step, newPercent);
        return buildResponse(experiment, "Traffic updated to " + newPercent + "%");
    }

    public ExperimentResponse completeExperiment(String experimentId) {
        Experiment experiment = experimentStore.get(experimentId);
        if (experiment == null) {
            return ExperimentResponse.builder()
                    .experimentId(experimentId)
                    .status(ExperimentStatus.CANCELLED)
                    .message("Experiment not found")
                    .build();
        }

        experiment.setStatus(ExperimentStatus.COMPLETED);
        experiment.setActualEndTime(LocalDateTime.now());
        experiment.setCurrentTrafficPercent(0);

        removeTraffic(experiment);
        qualityGateService.unregisterExperiment(experimentId);

        log.info("Experiment completed: id={}, name={}", experimentId, experiment.getName());
        return buildResponse(experiment, "Experiment completed");
    }

    public ExperimentResponse graduateExperiment(String experimentId) {
        Experiment experiment = experimentStore.get(experimentId);
        if (experiment == null) {
            return ExperimentResponse.builder()
                    .experimentId(experimentId)
                    .status(ExperimentStatus.CANCELLED)
                    .message("Experiment not found")
                    .build();
        }

        experiment.setStatus(ExperimentStatus.GRADUATED);
        experiment.setActualEndTime(LocalDateTime.now());
        experiment.setCurrentTrafficPercent(100);

        applyFullTraffic(experiment);
        qualityGateService.unregisterExperiment(experimentId);

        log.info("Experiment graduated: id={}, name={}, version promoted", experimentId, experiment.getName());
        return buildResponse(experiment, "Experiment graduated, version promoted");
    }

    public ExperimentResponse rollbackExperiment(String experimentId, String reason) {
        Experiment experiment = experimentStore.get(experimentId);
        if (experiment == null) {
            return ExperimentResponse.builder()
                    .experimentId(experimentId)
                    .status(ExperimentStatus.CANCELLED)
                    .message("Experiment not found")
                    .build();
        }

        experiment.setStatus(ExperimentStatus.ROLLBACKED);
        experiment.setActualEndTime(LocalDateTime.now());
        experiment.setCurrentTrafficPercent(0);

        removeTraffic(experiment);
        qualityGateService.unregisterExperiment(experimentId);

        log.warn("Experiment rolled back: id={}, reason={}", experimentId, reason);
        return buildResponse(experiment, "Rolled back: " + reason);
    }

    public Experiment getExperiment(String experimentId) {
        return experimentStore.get(experimentId);
    }

    public List<Experiment> getExperimentsByService(String serviceName) {
        return experimentStore.values().stream()
                .filter(e -> e.getServiceName().equals(serviceName))
                .collect(Collectors.toList());
    }

    public List<Experiment> getExperimentsByGroup(String serviceName, String group) {
        String groupKey = getGroupKey(serviceName, group);
        return groupExperiments.getOrDefault(groupKey, new ArrayList<>());
    }

    public List<Experiment> getRunningExperiments(String serviceName) {
        return experimentStore.values().stream()
                .filter(e -> e.getServiceName().equals(serviceName) &&
                        e.getStatus() == ExperimentStatus.RUNNING)
                .collect(Collectors.toList());
    }

    public List<Experiment> getAllExperiments() {
        return new ArrayList<>(experimentStore.values());
    }

    private boolean checkConflict(Experiment newExperiment) {
        List<Experiment> running = getRunningExperiments(newExperiment.getServiceName());

        for (Experiment exp : running) {
            if (exp.getId().equals(newExperiment.getId())) {
                continue;
            }

            if (exp.getExperimentGroup() != null &&
                    exp.getExperimentGroup().equals(newExperiment.getExperimentGroup())) {
                if (exp.getTrafficMatchRules() != null && newExperiment.getTrafficMatchRules() != null) {
                    for (String key : newExperiment.getTrafficMatchRules().keySet()) {
                        String newValue = newExperiment.getTrafficMatchRules().get(key);
                        String existingValue = exp.getTrafficMatchRules().get(key);
                        if (newValue != null && newValue.equals(existingValue)) {
                            log.warn("Experiment conflict detected: same match rule for key={}", key);
                            return false;
                        }
                    }
                }
            }
        }

        return true;
    }

    private void applyTraffic(Experiment experiment) {
        releaseService.createRelease(buildReleaseRequest(experiment));
    }

    private void applyFullTraffic(Experiment experiment) {
        releaseService.createRelease(buildReleaseRequest(experiment));
    }

    private void removeTraffic(Experiment experiment) {
        releaseService.rollbackRelease(experiment.getId(), "Experiment ended");
    }

    private com.grayrelease.common.dto.ReleaseRequest buildReleaseRequest(Experiment experiment) {
        MetricThreshold threshold = null;
        if (experiment.getGuardrailMetrics() != null && !experiment.getGuardrailMetrics().isEmpty()) {
            threshold = experiment.getGuardrailMetrics().get(0);
        }

        return com.grayrelease.common.dto.ReleaseRequest.builder()
                .serviceName(experiment.getServiceName())
                .strategy(experiment.getStrategy())
                .stableVersion(experiment.getStableVersion())
                .canaryVersion(experiment.getExperimentVersion())
                .canaryImage(experiment.getExperimentImage())
                .stepTrafficPercents(experiment.getStepTrafficPercents())
                .matchRules(experiment.getTrafficMatchRules())
                .threshold(threshold)
                .createdBy(experiment.getOwner())
                .build();
    }

    private String getGroupKey(String serviceName, String group) {
        return serviceName + ":" + (group != null ? group : "default");
    }

    private ExperimentResponse buildResponse(Experiment experiment, String message) {
        return ExperimentResponse.builder()
                .experimentId(experiment.getId())
                .name(experiment.getName())
                .serviceName(experiment.getServiceName())
                .experimentGroup(experiment.getExperimentGroup())
                .strategy(experiment.getStrategy())
                .status(experiment.getStatus())
                .stableVersion(experiment.getStableVersion())
                .experimentVersion(experiment.getExperimentVersion())
                .currentTrafficPercent(experiment.getCurrentTrafficPercent())
                .maxTrafficPercent(experiment.getMaxTrafficPercent())
                .startTime(experiment.getStartTime())
                .endTime(experiment.getEndTime())
                .message(message)
                .build();
    }
}