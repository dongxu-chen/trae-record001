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
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
@RequiredArgsConstructor
public class BlueGreenReleaseStrategy implements ReleaseStrategyHandler {

    private final VersionManager versionManager;
    private final K8sDeploymentService k8sDeploymentService;
    private final TrafficRoutingService trafficRoutingService;

    private final ConcurrentHashMap<String, ReleaseRecord> releaseStore = new ConcurrentHashMap<>();

    @Override
    public ReleaseResponse execute(ReleaseRequest request) {
        log.info("Starting blue-green release for service: {}, blue(stable): {}, green(canary): {}",
                request.getServiceName(), request.getStableVersion(), request.getCanaryVersion());

        String releaseId = IdGenerator.generateReleaseId(request.getServiceName());

        ReleaseRecord record = ReleaseRecord.builder()
                .id(releaseId)
                .serviceName(request.getServiceName())
                .strategy(ReleaseStrategy.BLUE_GREEN)
                .status(ReleaseStatus.RUNNING)
                .stableVersion(request.getStableVersion())
                .canaryVersion(request.getCanaryVersion())
                .canaryTrafficPercent(0)
                .threshold(request.getThreshold())
                .startTime(LocalDateTime.now())
                .createdBy(request.getCreatedBy())
                .build();

        releaseStore.put(releaseId, record);

        boolean deployed = k8sDeploymentService.deployGreenVersion(
                request.getServiceName(),
                request.getCanaryVersion(),
                request.getCanaryImage()
        );

        if (!deployed) {
            record.setStatus(ReleaseStatus.PENDING);
            return buildResponse(record, "Failed to deploy green version");
        }

        log.info("Blue-green release started: releaseId={}, green version deployed, traffic still on blue", releaseId);
        return buildResponse(record, "Green version deployed, ready for traffic switch");
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

        if (step == 0) {
            record.setCanaryTrafficPercent(100);
            trafficRoutingService.switchToGreen(
                    record.getServiceName(),
                    record.getStableVersion(),
                    record.getCanaryVersion()
            );
            log.info("Blue-green traffic switched: releaseId={}, traffic moved to green", releaseId);
            return buildResponse(record, "Traffic switched to green version");
        }

        return buildResponse(record, "Blue-green in progress");
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

        versionManager.promoteVersion(record.getServiceName(), record.getCanaryVersion());

        k8sDeploymentService.promoteGreenToStable(
                record.getServiceName(),
                record.getCanaryVersion()
        );

        k8sDeploymentService.scaleDownBlueVersion(
                record.getServiceName(),
                record.getStableVersion()
        );

        log.info("Blue-green release completed: releaseId={}", releaseId);
        return buildResponse(record, "Blue-green release completed, blue version scaled down");
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

        trafficRoutingService.switchToBlue(
                record.getServiceName(),
                record.getStableVersion(),
                record.getCanaryVersion()
        );

        k8sDeploymentService.rollbackGreenVersion(
                record.getServiceName(),
                record.getCanaryVersion()
        );

        log.warn("Blue-green release rolled back: releaseId={}, reason={}", releaseId, reason);
        return buildResponse(record, "Rolled back to blue: " + reason);
    }

    @Override
    public boolean supports(ReleaseStrategy strategy) {
        return ReleaseStrategy.BLUE_GREEN == strategy;
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