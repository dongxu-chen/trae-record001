package com.apigateway.core.health;

import com.apigateway.core.dto.ApiResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

import java.util.List;
import java.util.Map;

/**
 * 健康检查REST API控制器
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@RestController
@RequestMapping("/api/health")
@RequiredArgsConstructor
public class HealthCheckController {

    private final ApiHealthCheckService healthCheckService;

    /**
     * 获取当前健康状态
     *
     * @return 健康状态信息
     */
    @GetMapping("/status")
    public Mono<ResponseEntity<ApiResponse<Map<String, Object>>>> getHealthStatus() {
        log.info("获取健康状态");
        return healthCheckService.getHealthStatus()
                .map(status -> ResponseEntity.ok(ApiResponse.success("获取健康状态成功", status)))
                .onErrorResume(e -> {
                    log.error("获取健康状态失败", e);
                    return Mono.just(ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                            .body(ApiResponse.error("获取健康状态失败: " + e.getMessage())));
                });
    }

    /**
     * 获取历史探测记录
     *
     * @param limit 返回记录数量限制，默认返回全部
     * @return 历史记录列表
     */
    @GetMapping("/history")
    public Mono<ResponseEntity<ApiResponse<List<HealthCheckResult>>>> getHealthHistory(
            @RequestParam(defaultValue = "0") int limit) {
        log.info("获取健康检查历史记录，limit: {}", limit);
        return healthCheckService.getHealthHistory(limit)
                .map(history -> ResponseEntity.ok(ApiResponse.success("获取历史记录成功", history)))
                .onErrorResume(e -> {
                    log.error("获取历史记录失败", e);
                    return Mono.just(ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                            .body(ApiResponse.error("获取历史记录失败: " + e.getMessage())));
                });
    }

    /**
     * 手动触发巡检
     *
     * @return 巡检结果列表
     */
    @PostMapping("/check")
    public Mono<ResponseEntity<ApiResponse<List<HealthCheckResult>>>> manualCheck() {
        log.info("手动触发健康检查");
        return healthCheckService.checkAllEndpoints()
                .collectList()
                .map(results -> ResponseEntity.ok(ApiResponse.success("手动巡检完成", results)))
                .onErrorResume(e -> {
                    log.error("手动巡检失败", e);
                    return Mono.just(ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                            .body(ApiResponse.error("手动巡检失败: " + e.getMessage())));
                });
    }

    /**
     * 获取监控接口列表
     *
     * @return 监控接口列表
     */
    @GetMapping("/endpoints")
    public Mono<ResponseEntity<ApiResponse<List<HealthCheckEndpoint>>>> getEndpoints() {
        log.info("获取监控接口列表");
        List<HealthCheckEndpoint> endpoints = healthCheckService.getAllEndpoints();
        return Mono.just(ResponseEntity.ok(ApiResponse.success("获取监控接口列表成功", endpoints)));
    }

    /**
     * 新增监控接口
     *
     * @param endpoint 接口配置
     * @return 新增结果
     */
    @PostMapping("/endpoints")
    public Mono<ResponseEntity<ApiResponse<HealthCheckEndpoint>>> addEndpoint(
            @Valid @RequestBody HealthCheckEndpoint endpoint) {
        log.info("新增监控接口: {} - {}", endpoint.getName(), endpoint.getUrl());
        try {
            healthCheckService.addEndpoint(endpoint);
            return Mono.just(ResponseEntity.status(HttpStatus.CREATED)
                    .body(ApiResponse.success("新增监控接口成功", endpoint)));
        } catch (Exception e) {
            log.error("新增监控接口失败", e);
            return Mono.just(ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ApiResponse.error("新增监控接口失败: " + e.getMessage())));
        }
    }
}
