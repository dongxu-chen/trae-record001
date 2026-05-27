package com.grayrelease.release.service;

import com.grayrelease.common.dto.ReleaseRequest;
import com.grayrelease.common.dto.ReleaseResponse;
import com.grayrelease.common.enums.ReleaseStatus;
import com.grayrelease.common.enums.ReleaseStrategy;
import com.grayrelease.common.model.ReleaseVersion;
import com.grayrelease.release.strategy.ReleaseStrategyHandler;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
@RequiredArgsConstructor
public class ReleaseService {

    private final List<ReleaseStrategyHandler> strategyHandlers;
    private final VersionManager versionManager;
    private final AutoRollbackEngine autoRollbackEngine;
    private final ImageRegistryChecker imageRegistryChecker;

    private final Map<String, ReleaseStrategy> activeReleases = new ConcurrentHashMap<>();

    private final Map<String, ReleaseRequest> releaseRequests = new ConcurrentHashMap<>();

    @Value("${rollback.check-image-exists:true}")
    private boolean checkImageExistsBeforeRollback;

    @Value("${rollback.force-on-automatic:true}")
    private boolean forceRollbackOnAutomaticTrigger;

    public ReleaseResponse createRelease(ReleaseRequest request) {
        log.info("Creating release: service={}, strategy={}", request.getServiceName(), request.getStrategy());

        versionManager.initializeDefaultVersions(
                request.getServiceName(),
                request.getStableVersion(),
                "default-image:latest"
        );

        ReleaseStrategyHandler handler = getHandler(request.getStrategy());
        ReleaseResponse response = handler.execute(request);

        if (response.getStatus() == ReleaseStatus.RUNNING) {
            activeReleases.put(response.getReleaseId(), request.getStrategy());
            releaseRequests.put(response.getReleaseId(), request);
            autoRollbackEngine.registerRelease(response.getReleaseId(), request.getThreshold());
        }

        return response;
    }

    public ReleaseResponse progressRelease(String releaseId, int step) {
        ReleaseStrategy strategy = activeReleases.get(releaseId);
        if (strategy == null) {
            return ReleaseResponse.builder()
                    .releaseId(releaseId)
                    .status(ReleaseStatus.ROLLED_BACK)
                    .message("Active release not found")
                    .build();
        }

        ReleaseStrategyHandler handler = getHandler(strategy);
        return handler.progress(releaseId, step);
    }

    public ReleaseResponse completeRelease(String releaseId) {
        ReleaseStrategy strategy = activeReleases.get(releaseId);
        if (strategy == null) {
            return ReleaseResponse.builder()
                    .releaseId(releaseId)
                    .status(ReleaseStatus.ROLLED_BACK)
                    .message("Active release not found")
                    .build();
        }

        ReleaseStrategyHandler handler = getHandler(strategy);
        ReleaseResponse response = handler.complete(releaseId);

        activeReleases.remove(releaseId);
        releaseRequests.remove(releaseId);
        autoRollbackEngine.unregisterRelease(releaseId);

        return response;
    }

    public ReleaseResponse rollbackRelease(String releaseId, String reason) {
        ReleaseStrategy strategy = activeReleases.get(releaseId);
        if (strategy == null) {
            return ReleaseResponse.builder()
                    .releaseId(releaseId)
                    .status(ReleaseStatus.ROLLED_BACK)
                    .message("Active release not found")
                    .build();
        }

        ReleaseRequest request = releaseRequests.get(releaseId);

        if (checkImageExistsBeforeRollback && request != null) {
            String rollbackImage = getRollbackImage(request);
            boolean isAutomaticRollback = reason != null && reason.toLowerCase().contains("auto");

            ImageRegistryChecker.RollbackCheckResult checkResult =
                    imageRegistryChecker.checkRollbackImage(
                            request.getServiceName(),
                            request.getStableVersion(),
                            rollbackImage
                    );

            if (!checkResult.isCanRollback() && !isAutomaticRollback) {
                log.error("Rollback blocked: {}", checkResult.getBlockedReason());
                return ReleaseResponse.builder()
                        .releaseId(releaseId)
                        .serviceName(request.getServiceName())
                        .strategy(strategy)
                        .status(ReleaseStatus.RUNNING)
                        .stableVersion(request.getStableVersion())
                        .canaryVersion(request.getCanaryVersion())
                        .message("Rollback blocked: " + checkResult.getBlockedReason())
                        .build();
            }

            if (!checkResult.isCanRollback() && isAutomaticRollback && !forceRollbackOnAutomaticTrigger) {
                log.warn("Automatic rollback blocked but force not enabled: {}", checkResult.getBlockedReason());
                return ReleaseResponse.builder()
                        .releaseId(releaseId)
                        .serviceName(request.getServiceName())
                        .strategy(strategy)
                        .status(ReleaseStatus.RUNNING)
                        .stableVersion(request.getStableVersion())
                        .canaryVersion(request.getCanaryVersion())
                        .message("Automatic rollback blocked: " + checkResult.getBlockedReason())
                        .build();
            }

            if (!checkResult.isCanRollback() && isAutomaticRollback && forceRollbackOnAutomaticTrigger) {
                log.warn("Automatic rollback forced despite check failure: {}", checkResult.getBlockedReason());
            }
        }

        ReleaseStrategyHandler handler = getHandler(strategy);
        ReleaseResponse response = handler.rollback(releaseId, reason);

        activeReleases.remove(releaseId);
        releaseRequests.remove(releaseId);
        autoRollbackEngine.unregisterRelease(releaseId);

        return response;
    }

    private String getRollbackImage(ReleaseRequest request) {
        ReleaseVersion stableVersion = versionManager.getStableVersion(request.getServiceName());
        if (stableVersion != null && stableVersion.getImage() != null) {
            return stableVersion.getImage();
        }
        return request.getServiceName() + ":" + request.getStableVersion();
    }

    public ImageRegistryChecker.RollbackCheckResult preCheckRollback(String releaseId) {
        ReleaseRequest request = releaseRequests.get(releaseId);
        if (request == null) {
            ImageRegistryChecker.RollbackCheckResult result = new ImageRegistryChecker.RollbackCheckResult();
            result.setCanRollback(false);
            result.setBlockedReason("Release not found");
            return result;
        }

        String rollbackImage = getRollbackImage(request);
        return imageRegistryChecker.checkRollbackImage(
                request.getServiceName(),
                request.getStableVersion(),
                rollbackImage
        );
    }

    public Map<String, ReleaseStrategy> getActiveReleases() {
        return new ConcurrentHashMap<>(activeReleases);
    }

    private ReleaseStrategyHandler getHandler(ReleaseStrategy strategy) {
        return strategyHandlers.stream()
                .filter(h -> h.supports(strategy))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("No handler for strategy: " + strategy));
    }
}