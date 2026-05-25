package com.coupon.controller;

import com.coupon.abtest.splitter.TrafficSplitter;
import com.coupon.abtest.service.ExperimentService;
import com.coupon.common.ApiResponse;
import com.coupon.model.ExperimentConfig;
import com.coupon.model.enums.SceneType;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/v1/experiment")
public class ExperimentController {

    private final ExperimentService experimentService;
    private final TrafficSplitter trafficSplitter;

    public ExperimentController(ExperimentService experimentService, TrafficSplitter trafficSplitter) {
        this.experimentService = experimentService;
        this.trafficSplitter = trafficSplitter;
    }

    @PostMapping
    public ApiResponse<ExperimentConfig> createExperiment(@RequestBody ExperimentConfig config) {
        log.info("Create experiment: {}", config.getExperimentId());
        ExperimentConfig created = experimentService.createExperiment(config);
        if (created == null) {
            return ApiResponse.error("实验创建失败");
        }
        return ApiResponse.success(created);
    }

    @GetMapping("/{experimentId}")
    public ApiResponse<ExperimentConfig> getExperiment(@PathVariable String experimentId) {
        ExperimentConfig config = experimentService.getExperiment(experimentId);
        if (config == null) {
            return ApiResponse.notFound("实验不存在");
        }
        return ApiResponse.success(config);
    }

    @GetMapping
    public ApiResponse<List<ExperimentConfig>> getAllExperiments() {
        return ApiResponse.success(experimentService.getAllExperiments());
    }

    @PutMapping
    public ApiResponse<ExperimentConfig> updateExperiment(@RequestBody ExperimentConfig config) {
        log.info("Update experiment: {}", config.getExperimentId());
        experimentService.updateExperiment(config);
        return ApiResponse.success(config);
    }

    @DeleteMapping("/{experimentId}")
    public ApiResponse<Void> deleteExperiment(@PathVariable String experimentId) {
        log.info("Delete experiment: {}", experimentId);
        experimentService.deleteExperiment(experimentId);
        return ApiResponse.success();
    }

    @GetMapping("/scene/{sceneCode}")
    public ApiResponse<ExperimentConfig> getExperimentByScene(@PathVariable int sceneCode) {
        SceneType sceneType = SceneType.fromCode(sceneCode);
        ExperimentConfig config = experimentService.getExperimentByScene(sceneType);
        if (config == null) {
            return ApiResponse.notFound("场景实验不存在");
        }
        return ApiResponse.success(config);
    }

    @GetMapping("/assign")
    public ApiResponse<Map<String, Object>> assignUserToGroup(
            @RequestParam String userId,
            @RequestParam int sceneCode) {
        SceneType sceneType = SceneType.fromCode(sceneCode);
        String groupId = experimentService.assignUserToGroup(userId, sceneType);
        ExperimentConfig.ExperimentGroup group =
                experimentService.getExperimentGroup(userId, sceneType);

        return ApiResponse.success(Map.of(
                "userId", userId,
                "scene", sceneType.name(),
                "groupId", groupId != null ? groupId : "none",
                "isRlEnabled", group != null && Boolean.TRUE.equals(group.getIsRlEnabled()),
                "experimentId", group != null ? experimentService.getExperimentByScene(sceneType).getExperimentId() : null
        ));
    }

    @PostMapping("/refresh")
    public ApiResponse<Void> refreshCache() {
        experimentService.refreshCache();
        return ApiResponse.success();
    }

    @GetMapping("/balance/{experimentId}")
    public ApiResponse<TrafficSplitter.BalanceCheckResult> checkExperimentBalance(
            @PathVariable String experimentId) {
        TrafficSplitter.BalanceCheckResult result = experimentService.checkExperimentBalance(experimentId);
        return ApiResponse.success(result);
    }

    @GetMapping("/strata")
    public ApiResponse<List<TrafficSplitter.StratumInfo>> getAllStrataInfo() {
        return ApiResponse.success(experimentService.getAllStrataInfo());
    }

    @GetMapping("/stratum/{userId}")
    public ApiResponse<Map<String, Object>> getUserStratum(
            @PathVariable String userId,
            @RequestParam(defaultValue = "0") int sceneCode) {
        com.coupon.model.UserProfile profile = new com.coupon.model.UserProfile();
        profile.setUserId(userId);
        String stratumId = trafficSplitter.calculateStratumId(profile);
        return ApiResponse.success(Map.of(
                "userId", userId,
                "stratumId", stratumId
        ));
    }
}
