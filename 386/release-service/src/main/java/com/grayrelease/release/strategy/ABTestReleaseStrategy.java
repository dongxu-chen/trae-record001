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
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
@RequiredArgsConstructor
public class ABTestReleaseStrategy implements ReleaseStrategyHandler {

    private final VersionManager versionManager;
    private final K8sDeploymentService k8sDeploymentService;
    private final TrafficRoutingService trafficRoutingService;

    private final ConcurrentHashMap<String, ReleaseRecord> releaseStore = new ConcurrentHashMap<>();

    @Override
    public ReleaseResponse execute(ReleaseRequest request) {
        log.info("Starting A/B test release for service: {}, stable: {}, canary: {}",
                request.getServiceName(), request.getStableVersion(), request.getCanaryVersion());

        String releaseId = IdGenerator.generateReleaseId(request.getServiceName());

        ReleaseRecord record = ReleaseRecord.builder()
                .id(releaseId)
                .serviceName(request.getServiceName())
                .strategy(ReleaseStrategy.AB_TEST)
                .status(ReleaseStatus.RUNNING)
                .stableVersion(request.getStableVersion())
                .canaryVersion(request.getCanaryVersion())
                .canaryTrafficPercent(50)
                .matchRules(request.getMatchRules())
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

        Map<String, String> matchRules = request.getMatchRules();
        if (matchRules != null && !matchRules.isEmpty()) {
            trafficRoutingService.updateABTestRouting(
                    request.getServiceName(),
                    request.getStableVersion(),
                    request.getCanaryVersion(),
                    matchRules
            );
        } else {
            trafficRoutingService.updateTrafficSplit(
                    request.getServiceName(),
                    request.getStableVersion(),
                    request.getCanaryVersion(),
                    50
            );
        }

        log.info("A/B test release started: releaseId={}", releaseId);
        return buildResponse(record, "A/B test release started");
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

        log.info("A/B test release progress: releaseId={}, step={}", releaseId, step);
        return buildResponse(record, "A/B test in progress");
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

        log.info("A/B test release completed: releaseId={}", releaseId);
        return buildResponse(record, "A/B test release completed");
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

        log.warn("A/B test release rolled back: releaseId={}, reason={}", releaseId, reason);
        return buildResponse(record, "Rolled back: " + reason);
    }

    @Override
    public boolean supports(ReleaseStrategy strategy) {
        return ReleaseStrategy.AB_TEST == strategy;
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