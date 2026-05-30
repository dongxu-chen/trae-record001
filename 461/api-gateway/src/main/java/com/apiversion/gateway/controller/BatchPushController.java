package com.apiversion.gateway.controller;

import com.apiversion.gateway.ratelimit.BatchPushManager;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

@Slf4j
@RestController
@RequestMapping("/api/batch-push")
@RequiredArgsConstructor
@Tag(name = "分批推送管理", description = "分批灰度推送管理API")
public class BatchPushController {

    private final BatchPushManager batchPushManager;

    @PostMapping("/{apiPath}/start")
    @Operation(summary = "启动分批推送", description = "启动指定API的分批灰度推送")
    public Mono<String> startBatchPush(
            @Parameter(description = "API路径") @PathVariable String apiPath,
            @RequestBody BatchPushManager.BatchConfig config) {
        log.info("启动分批推送: apiPath={}, config={}", apiPath, config);
        return batchPushManager.startBatchPush(apiPath, config)
                .then(Mono.just("分批推送已启动: " + apiPath));
    }

    @PostMapping("/{apiPath}/advance")
    @Operation(summary = "推进批次", description = "将推送推进到下一个批次")
    public Mono<String> advanceBatch(
            @Parameter(description = "API路径") @PathVariable String apiPath) {
        log.info("推进批次: apiPath={}", apiPath);
        return batchPushManager.advanceBatch(apiPath)
                .then(Mono.just("批次已推进: " + apiPath));
    }

    @PostMapping("/{apiPath}/stop")
    @Operation(summary = "停止分批推送", description = "停止指定API的分批推送")
    public Mono<String> stopBatchPush(
            @Parameter(description = "API路径") @PathVariable String apiPath) {
        log.info("停止分批推送: apiPath={}", apiPath);
        return batchPushManager.stopBatchPush(apiPath)
                .then(Mono.just("分批推送已停止: " + apiPath));
    }

    @GetMapping("/{apiPath}/status")
    @Operation(summary = "获取推送状态", description = "获取指定API的分批推送状态")
    public Mono<BatchPushManager.BatchPushStatus> getPushStatus(
            @Parameter(description = "API路径") @PathVariable String apiPath) {
        return batchPushManager.getPushStatus(apiPath);
    }

    @PostMapping("/{apiPath}/auto-config")
    @Operation(summary = "自动配置推送参数", description = "根据兼容性评估自动配置推送参数")
    public Mono<BatchPushManager.BatchConfig> autoConfigurePush(
            @Parameter(description = "API路径") @PathVariable String apiPath,
            @RequestBody AutoConfigRequest request) {
        log.info("自动配置推送参数: apiPath={}, backwardScore={}, migrationComplexity={}",
                apiPath, request.getBackwardCompatibilityScore(), request.getMigrationComplexity());

        BatchPushManager.BatchConfig config = calculateOptimalConfig(
                request.getBackwardCompatibilityScore(),
                request.getMigrationComplexity()
        );

        return Mono.just(config);
    }

    private BatchPushManager.BatchConfig calculateOptimalConfig(
            Integer backwardCompatibilityScore,
            Integer migrationComplexity) {

        int score = backwardCompatibilityScore != null ? backwardCompatibilityScore : 50;
        int complexity = migrationComplexity != null ? migrationComplexity : 50;

        int totalBatches;
        int batchSize;
        long batchIntervalMs;

        if (score >= 80 && complexity <= 30) {
            totalBatches = 5;
            batchSize = 5000;
            batchIntervalMs = 3600000;
        } else if (score >= 60 && complexity <= 50) {
            totalBatches = 10;
            batchSize = 2000;
            batchIntervalMs = 7200000;
        } else if (score >= 40 && complexity <= 70) {
            totalBatches = 20;
            batchSize = 1000;
            batchIntervalMs = 14400000;
        } else {
            totalBatches = 50;
            batchSize = 500;
            batchIntervalMs = 28800000;
        }

        BatchPushManager.BatchConfig config = new BatchPushManager.BatchConfig();
        config.setTotalBatches(totalBatches);
        config.setBatchSize(batchSize);
        config.setBatchIntervalMs(batchIntervalMs);
        config.setAllowAnonymous(false);

        return config;
    }

    @lombok.Data
    public static class AutoConfigRequest {
        private Integer backwardCompatibilityScore;
        private Integer migrationComplexity;
    }
}
