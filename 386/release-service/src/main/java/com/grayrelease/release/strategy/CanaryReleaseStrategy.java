package com.grayrelease.release.strategy;

import com.grayrelease.common.dto.ReleaseRequest;
import com.grayrelease.common.dto.ReleaseResponse;
import com.grayrelease.common.enums.ReleaseStatus;
import com.grayrelease.common.enums.ReleaseStrategy;
import com.grayrelease.common.model.ReleaseRecord;
import com.grayrelease.common.util.IdGenerator;
import com.grayrelease.release.service.K8sDeploymentService;
import com.grayrelease.release.service.TrafficRoutingService;
import com.grayrelease.release.service.VersionManager;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
@RequiredArgsConstructor
public class CanaryReleaseStrategy implements ReleaseStrategyHandler {

    private final VersionManager versionManager;
    private final K8sDeploymentService k8sDeploymentService;
    private final TrafficRoutingService trafficRoutingService;

    private final ConcurrentHashMap<String, ReleaseRecord> releaseStore = new ConcurrentHashMap<>();

    @Override
    public ReleaseResponse execute(ReleaseRequest request) {
        log.info("Starting canary release for service: {}, stable: {}, canary: {}",
                request.getServiceName(), request.getStableVersion(), request.getCanaryVersion());

        String releaseId = IdGenerator.generateReleaseId(request.getServiceName());

        List<Integer> stepPercents = request.getStepTrafficPercents();
        if (stepPercents == null || stepPercents.isEmpty()) {
            stepPercents = List.of(5, 10, 25, 50, 100);
        }

        ReleaseRecord record = ReleaseRecord.builder()
                .id(releaseId)
                .serviceName(request.getServiceName())
                .strategy(ReleaseStrategy.CANARY)
                .status(ReleaseStatus.RUNNING)
                .stableVersion(request.getStableVersion())
                .canaryVersion(request.getCanaryVersion())
                .canaryTrafficPercent(stepPercents.get(0))
                .stepTrafficPercents(stepPercents)
                .currentStep(0)
                .threshold(request.getThreshold())
                .startTime(LocalDateTime.now())
                .createdBy(request.getCreatedBy())
                .build();

        releaseStore.put(releaseId, record);

        boolean deployed = k8sDeploymentService.deployCanaryVersion(
                request.getServiceName(),
                request.getCanaryVersion(),
                request.getCanaryImage()
        );

        if (!deployed) {
            record.setStatus(ReleaseStatus.PENDING);
            return buildResponse(record, "Failed to deploy canary version");
        }

        trafficRoutingService.updateTrafficSplit(
                request.getServiceName(),
                request.getStableVersion(),
                request.getCanaryVersion(),
                stepPercents.get(0)
        );

        log.info("Canary release started: releaseId={}, initialTraffic={}%", releaseId, stepPercents.get(0));
        return buildResponse(record, "Canary release started");
    }

    @Override
    public ReleaseResponse progress(String releaseId, int step) {
        ReleaseRecord record = releaseStore.get(releaseId);
        if (record == null) {
            return ReleaseResponse.builder()
                    .releaseId(releaseId)
                    .status(ReleaseStatus.ROLLED_BACK)
                    .message("Release not found")
                    .build();
        }

        List<Integer> steps = record.getStepTrafficPercents();
        if (step >= steps.size()) {
            return complete(releaseId);
        }

        int newPercent = steps.get(step);
        record.setCurrentStep(step);
        record.setCanaryTrafficPercent(newPercent);

        trafficRoutingService.updateTrafficSplit(
                record.getServiceName(),
                record.getStableVersion(),
                record.getCanaryVersion(),
                newPercent
        );

        log.info("Canary release progressed: releaseId={}, step={}, traffic={}%", releaseId, step, newPercent);
        return buildResponse(record, "Traffic updated to " + newPercent + "%");
    }

    @Override
    public ReleaseResponse complete(String releaseId) {
        ReleaseRecord record = releaseStore.get(releaseId);
        if (record == null) {
            return ReleaseResponse.builder()
                    .releaseId(releaseId)
                    .status(ReleaseStatus.ROLLED_BACK)
                    .message("Release not found")
                    .build();
        }

        record.setStatus(ReleaseStatus.COMPLETED);
        record.setCanaryTrafficPercent(100);
        record.setEndTime(LocalDateTime.now());

        trafficRoutingService.updateTrafficSplit(
                record.getServiceName(),
                record.getStableVersion(),
                record.getCanaryVersion(),
                100
        );

        versionManager.promoteVersion(record.getServiceName(), record.getCanaryVersion());

        k8sDeploymentService.promoteCanaryToStable(
                record.getServiceName(),
                record.getCanaryVersion()
        );

        log.info("Canary release completed: releaseId={}", releaseId);
        return buildResponse(record, "Canary release completed successfully");
    }

    @Override
    public ReleaseResponse rollback(String releaseId, String reason) {
        ReleaseRecord record = releaseStore.get(releaseId);
        if (record == null) {
            return ReleaseResponse.builder()
                    .releaseId(releaseId)
                    .status(ReleaseStatus.ROLLED_BACK)
                    .message("Release not found")
                    .build();
        }

        record.setStatus(ReleaseStatus.ROLLED_BACK);
        record.setRollbackReason(reason);
        record.setEndTime(LocalDateTime.now());

        trafficRoutingService.updateTrafficSplit(
                record.getServiceName(),
                record.getStableVersion(),
                record.getCanaryVersion(),
                0
        );

        k8sDeploymentService.rollbackCanaryVersion(
                record.getServiceName(),
                record.getCanaryVersion()
        );

        log.warn("Canary release rolled back: releaseId={}, reason={}", releaseId, reason);
        return buildResponse(record, "Rolled back: " + reason);
    }

    @Override
    public boolean supports(ReleaseStrategy strategy) {
        return ReleaseStrategy.CANARY == strategy;
    }

    private ReleaseResponse buildResponse(ReleaseRecord record, String message) {
        return ReleaseResponse.builder()
                .releaseId(record.getId())
                .serviceName(record.getServiceName())
                .strategy(record.getStrategy())
                .status(record.getStatus())
                .stableVersion(record.getStableVersion())
                .canaryVersion(record.getCanaryVersion())
                .currentTrafficPercent(record.getCanaryTrafficPercent())
                .startTime(record.getStartTime())
                .message(message)
                .build();
    }
}