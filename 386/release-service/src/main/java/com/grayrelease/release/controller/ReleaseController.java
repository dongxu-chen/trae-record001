package com.grayrelease.release.controller;

import com.grayrelease.common.dto.ExperimentRequest;
import com.grayrelease.common.dto.ExperimentResponse;
import com.grayrelease.common.dto.ReleaseRequest;
import com.grayrelease.common.dto.ReleaseResponse;
import com.grayrelease.common.dto.VersionRequest;
import com.grayrelease.common.enums.ReleaseStrategy;
import com.grayrelease.common.enums.ReleaseWindowStatus;
import com.grayrelease.common.model.Experiment;
import com.grayrelease.common.model.ReleaseCalendar;
import com.grayrelease.common.model.ReleaseVersion;
import com.grayrelease.release.service.ExperimentManager;
import com.grayrelease.release.service.ImageRegistryChecker;
import com.grayrelease.release.service.K8sWeightedRoutingService;
import com.grayrelease.release.service.QualityGateService;
import com.grayrelease.release.service.ReleaseCalendarManager;
import com.grayrelease.release.service.ReleaseService;
import com.grayrelease.release.service.TrafficRoutingService;
import com.grayrelease.release.service.VersionManager;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/releases")
@RequiredArgsConstructor
public class ReleaseController {

    private final ReleaseService releaseService;
    private final VersionManager versionManager;
    private final TrafficRoutingService trafficRoutingService;
    private final ImageRegistryChecker imageRegistryChecker;
    private final ExperimentManager experimentManager;
    private final ReleaseCalendarManager calendarManager;
    private final QualityGateService qualityGateService;

    @PostMapping
    public ResponseEntity<ReleaseResponse> createRelease(@RequestBody ReleaseRequest request) {
        log.info("Create release request: service={}, strategy={}", request.getServiceName(), request.getStrategy());
        ReleaseResponse response = releaseService.createRelease(request);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/{releaseId}/progress")
    public ResponseEntity<ReleaseResponse> progressRelease(
            @PathVariable String releaseId,
            @RequestParam(defaultValue = "1") int step) {
        log.info("Progress release: releaseId={}, step={}", releaseId, step);
        ReleaseResponse response = releaseService.progressRelease(releaseId, step);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/{releaseId}/complete")
    public ResponseEntity<ReleaseResponse> completeRelease(@PathVariable String releaseId) {
        log.info("Complete release: releaseId={}", releaseId);
        ReleaseResponse response = releaseService.completeRelease(releaseId);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/{releaseId}/rollback")
    public ResponseEntity<ReleaseResponse> rollbackRelease(
            @PathVariable String releaseId,
            @RequestParam(required = false, defaultValue = "manual") String reason) {
        log.info("Rollback release: releaseId={}, reason={}", releaseId, reason);
        ReleaseResponse response = releaseService.rollbackRelease(releaseId, reason);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/active")
    public ResponseEntity<Map<String, ReleaseStrategy>> getActiveReleases() {
        return ResponseEntity.ok(releaseService.getActiveReleases());
    }

    @PostMapping("/versions")
    public ResponseEntity<ReleaseVersion> createVersion(@RequestBody VersionRequest request) {
        log.info("Create version: service={}, version={}", request.getServiceName(), request.getVersion());
        ReleaseVersion version = versionManager.createVersion(request);
        return ResponseEntity.ok(version);
    }

    @GetMapping("/versions/{serviceName}")
    public ResponseEntity<List<ReleaseVersion>> getVersions(@PathVariable String serviceName) {
        List<ReleaseVersion> versions = versionManager.getVersionsByService(serviceName);
        return ResponseEntity.ok(versions);
    }

    @GetMapping("/versions/{serviceName}/stable")
    public ResponseEntity<ReleaseVersion> getStableVersion(@PathVariable String serviceName) {
        ReleaseVersion version = versionManager.getStableVersion(serviceName);
        if (version == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(version);
    }

    @GetMapping("/strategies")
    public ResponseEntity<ReleaseStrategy[]> getStrategies() {
        return ResponseEntity.ok(ReleaseStrategy.values());
    }

    @GetMapping("/routes/{serviceName}")
    public ResponseEntity<K8sWeightedRoutingService.WeightedRouteStatus> getRouteStatus(@PathVariable String serviceName) {
        K8sWeightedRoutingService.WeightedRouteStatus status = trafficRoutingService.getRouteStatus(serviceName);
        return ResponseEntity.ok(status);
    }

    @GetMapping("/{releaseId}/rollback/check")
    public ResponseEntity<ImageRegistryChecker.RollbackCheckResult> preCheckRollback(@PathVariable String releaseId) {
        log.info("Pre-check rollback: releaseId={}", releaseId);
        ImageRegistryChecker.RollbackCheckResult result = releaseService.preCheckRollback(releaseId);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/images/check")
    public ResponseEntity<ImageRegistryChecker.ImageCheckResult> checkImage(@RequestParam String image) {
        log.info("Check image: {}", image);
        ImageRegistryChecker.ImageCheckResult result = imageRegistryChecker.checkImageExists(image);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/images/cache")
    public ResponseEntity<Map<String, ImageRegistryChecker.ImageInfo>> getImageCache() {
        return ResponseEntity.ok(imageRegistryChecker.getCachedImages());
    }

    @DeleteMapping("/images/cache")
    public ResponseEntity<String> clearImageCache() {
        imageRegistryChecker.clearCache();
        return ResponseEntity.ok("Image cache cleared");
    }

    @PostMapping("/experiments")
    public ResponseEntity<ExperimentResponse> createExperiment(@RequestBody ExperimentRequest request) {
        log.info("Create experiment: name={}, service={}", request.getName(), request.getServiceName());
        ExperimentResponse response = experimentManager.createExperiment(request);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/experiments/{experimentId}/start")
    public ResponseEntity<ExperimentResponse> startExperiment(@PathVariable String experimentId) {
        log.info("Start experiment: {}", experimentId);
        ExperimentResponse response = experimentManager.startExperiment(experimentId);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/experiments/{experimentId}/progress")
    public ResponseEntity<ExperimentResponse> progressExperiment(
            @PathVariable String experimentId,
            @RequestParam(defaultValue = "1") int step) {
        log.info("Progress experiment: {}, step={}", experimentId, step);
        ExperimentResponse response = experimentManager.progressExperiment(experimentId, step);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/experiments/{experimentId}/complete")
    public ResponseEntity<ExperimentResponse> completeExperiment(@PathVariable String experimentId) {
        log.info("Complete experiment: {}", experimentId);
        ExperimentResponse response = experimentManager.completeExperiment(experimentId);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/experiments/{experimentId}/graduate")
    public ResponseEntity<ExperimentResponse> graduateExperiment(@PathVariable String experimentId) {
        log.info("Graduate experiment: {}", experimentId);
        ExperimentResponse response = experimentManager.graduateExperiment(experimentId);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/experiments/{experimentId}/rollback")
    public ResponseEntity<ExperimentResponse> rollbackExperiment(
            @PathVariable String experimentId,
            @RequestParam(required = false, defaultValue = "manual") String reason) {
        log.info("Rollback experiment: {}, reason={}", experimentId, reason);
        ExperimentResponse response = experimentManager.rollbackExperiment(experimentId, reason);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/experiments")
    public ResponseEntity<List<Experiment>> getAllExperiments() {
        return ResponseEntity.ok(experimentManager.getAllExperiments());
    }

    @GetMapping("/experiments/{experimentId}")
    public ResponseEntity<Experiment> getExperiment(@PathVariable String experimentId) {
        Experiment experiment = experimentManager.getExperiment(experimentId);
        if (experiment == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(experiment);
    }

    @GetMapping("/experiments/service/{serviceName}")
    public ResponseEntity<List<Experiment>> getExperimentsByService(@PathVariable String serviceName) {
        return ResponseEntity.ok(experimentManager.getExperimentsByService(serviceName));
    }

    @GetMapping("/experiments/running/{serviceName}")
    public ResponseEntity<List<Experiment>> getRunningExperiments(@PathVariable String serviceName) {
        return ResponseEntity.ok(experimentManager.getRunningExperiments(serviceName));
    }

    @GetMapping("/experiments/{experimentId}/gate-status")
    public ResponseEntity<QualityGateService.GateStatus> getExperimentGateStatus(@PathVariable String experimentId) {
        QualityGateService.GateStatus status = qualityGateService.getGateStatus(experimentId);
        if (status == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(status);
    }

    @GetMapping("/gates/status")
    public ResponseEntity<Map<String, QualityGateService.GateStatus>> getAllGateStatuses() {
        return ResponseEntity.ok(qualityGateService.getAllGateStatuses());
    }

    @PostMapping("/calendar")
    public ResponseEntity<ReleaseCalendar> createCalendar(@RequestBody ReleaseCalendar calendar) {
        log.info("Create release calendar: service={}, name={}", calendar.getServiceName(), calendar.getName());
        ReleaseCalendar created = calendarManager.createCalendar(calendar);
        return ResponseEntity.ok(created);
    }

    @GetMapping("/calendar/{serviceName}/status")
    public ResponseEntity<ReleaseWindowStatus> getCurrentWindowStatus(@PathVariable String serviceName) {
        ReleaseWindowStatus status = calendarManager.getCurrentStatus(serviceName);
        return ResponseEntity.ok(status);
    }

    @GetMapping("/calendar/{serviceName}/can-release")
    public ResponseEntity<Boolean> canRelease(@PathVariable String serviceName,
                                               @RequestParam(required = false) Long time) {
        LocalDateTime checkTime = time != null ? LocalDateTime.ofEpochSecond(time, 0, java.time.ZoneOffset.UTC) : LocalDateTime.now();
        boolean canRelease = calendarManager.canRelease(serviceName, checkTime);
        return ResponseEntity.ok(canRelease);
    }

    @GetMapping("/calendar/{serviceName}/upcoming")
    public ResponseEntity<List<ReleaseCalendar>> getUpcomingWindows(
            @PathVariable String serviceName,
            @RequestParam(defaultValue = "7") int days) {
        List<ReleaseCalendar> windows = calendarManager.getUpcomingWindows(serviceName, days);
        return ResponseEntity.ok(windows);
    }

    @PostMapping("/calendar/{serviceName}/locks")
    public ResponseEntity<ReleaseCalendar.LockPeriod> createLockPeriod(
            @PathVariable String serviceName,
            @RequestBody ReleaseCalendar.LockPeriod lockPeriod) {
        log.info("Create lock period: service={}, name={}", serviceName, lockPeriod.getName());
        ReleaseCalendar.LockPeriod created = calendarManager.createLockPeriod(serviceName, lockPeriod);
        return ResponseEntity.ok(created);
    }

    @GetMapping("/calendar/{serviceName}/locks/active")
    public ResponseEntity<List<ReleaseCalendar.LockPeriod>> getActiveLocks(@PathVariable String serviceName) {
        return ResponseEntity.ok(calendarManager.getActiveLockPeriods(serviceName));
    }

    @GetMapping("/calendar/{serviceName}/locks/upcoming")
    public ResponseEntity<List<ReleaseCalendar.LockPeriod>> getUpcomingLocks(
            @PathVariable String serviceName,
            @RequestParam(defaultValue = "7") int days) {
        return ResponseEntity.ok(calendarManager.getUpcomingLockPeriods(serviceName, days));
    }

    @DeleteMapping("/calendar/{serviceName}/locks/{lockId}")
    public ResponseEntity<String> removeLockPeriod(@PathVariable String serviceName, @PathVariable String lockId) {
        boolean removed = calendarManager.removeLockPeriod(serviceName, lockId);
        if (removed) {
            return ResponseEntity.ok("Lock period removed");
        }
        return ResponseEntity.notFound().build();
    }

    @DeleteMapping("/calendar/{serviceName}")
    public ResponseEntity<String> clearServiceCalendar(@PathVariable String serviceName) {
        calendarManager.clearServiceCalendar(serviceName);
        return ResponseEntity.ok("Calendar cleared for service: " + serviceName);
    }
}