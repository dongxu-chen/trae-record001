package com.apigateway.core.replay;

import com.apigateway.core.dto.ApiResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

import java.util.List;
import java.util.Map;

/**
 * 请求重放REST API控制器
 * 提供重放管理接口，包括开启/关闭录制、查询录制列表、重放单个/批量请求、清空录制等
 * 采用响应式编程风格，返回统一的ApiResponse格式
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@RestController
@RequestMapping("/api/replay")
@RequiredArgsConstructor
@Validated
public class ReplayController {

    /**
     * 请求重放服务
     */
    private final RequestReplayService requestReplayService;

    /**
     * 开启/关闭录制功能
     *
     * @param request 开启/关闭请求
     * @return 操作结果
     */
    @PostMapping("/enable")
    public Mono<ApiResponse<Map<String, Object>>> setRecordingEnabled(@RequestBody @Valid EnableRequest request) {
        log.info("设置录制功能状态 - enabled: {}", request.isEnabled());

        requestReplayService.setRecordingEnabled(request.isEnabled());

        Map<String, Object> result = Map.of(
                "enabled", requestReplayService.isRecordingEnabled(),
                "environments", requestReplayService.getEnvironments()
        );

        return Mono.just(ApiResponse.success("录制功能已" + (request.isEnabled() ? "开启" : "关闭"), result));
    }

    /**
     * 获取录制功能状态
     *
     * @return 当前状态
     */
    @GetMapping("/status")
    public Mono<ApiResponse<Map<String, Object>>> getRecordingStatus() {
        log.debug("查询录制功能状态");

        Map<String, Object> result = Map.of(
                "enabled", requestReplayService.isRecordingEnabled(),
                "environments", requestReplayService.getEnvironments()
        );

        return Mono.just(ApiResponse.success(result));
    }

    /**
     * 查询录制的请求列表
     *
     * @param pageNum  页码（从0开始，默认0）
     * @param pageSize 每页大小（默认20）
     * @return 录制请求列表
     */
    @GetMapping("/requests")
    public Mono<ApiResponse<Map<String, Object>>> getRecordedRequests(
            @RequestParam(defaultValue = "0") int pageNum,
            @RequestParam(defaultValue = "20") int pageSize) {
        log.debug("查询录制请求列表 - pageNum: {}, pageSize: {}", pageNum, pageSize);

        if (pageNum < 0) {
            pageNum = 0;
        }
        if (pageSize <= 0 || pageSize > 100) {
            pageSize = 20;
        }

        return requestReplayService.getRecordedRequests(pageNum, pageSize)
                .map(ApiResponse::success)
                .onErrorResume(e -> {
                    log.error("查询录制请求列表失败 - error: {}", e.getMessage());
                    return Mono.just(ApiResponse.error("查询失败: " + e.getMessage()));
                });
    }

    /**
     * 根据ID获取单个录制请求详情
     *
     * @param id 请求ID
     * @return 录制请求详情
     */
    @GetMapping("/requests/{id}")
    public Mono<ApiResponse<RecordedRequest>> getRecordedRequest(@PathVariable String id) {
        log.debug("查询录制请求详情 - id: {}", id);

        return requestReplayService.getRecordedRequest(id)
                .map(request -> {
                    if (request == null) {
                        return ApiResponse.<RecordedRequest>error(404, "请求不存在: " + id);
                    }
                    return ApiResponse.success(request);
                })
                .switchIfEmpty(Mono.just(ApiResponse.error(404, "请求不存在: " + id)))
                .onErrorResume(e -> {
                    log.error("查询录制请求详情失败 - id: {}, error: {}", id, e.getMessage());
                    return Mono.just(ApiResponse.error("查询失败: " + e.getMessage()));
                });
    }

    /**
     * 重放单个请求
     *
     * @param id      请求ID
     * @param request 重放请求（包含目标环境）
     * @return 重放结果
     */
    @PostMapping("/replay/{id}")
    public Mono<ApiResponse<ReplayResult>> replayRequest(
            @PathVariable String id,
            @RequestBody(required = false) ReplaySingleRequest request) {
        String targetEnvironment = request != null ? request.getTargetEnvironment() : null;
        log.info("重放单个请求 - id: {}, targetEnvironment: {}", id, targetEnvironment);

        return requestReplayService.replayRequest(id, targetEnvironment)
                .map(result -> {
                    if (result.isSuccess()) {
                        return ApiResponse.success("重放成功", result);
                    } else {
                        return ApiResponse.<ReplayResult>builder()
                                .success(false)
                                .code(500)
                                .message("重放失败: " + result.getErrorMessage())
                                .data(result)
                                .build();
                    }
                })
                .onErrorResume(e -> {
                    log.error("重放请求失败 - id: {}, error: {}", id, e.getMessage());
                    return Mono.just(ApiResponse.error("重放失败: " + e.getMessage()));
                });
    }

    /**
     * 批量重放请求
     *
     * @param request 批量重放请求
     * @return 重放结果列表
     */
    @PostMapping("/replay/batch")
    public Mono<ApiResponse<List<ReplayResult>>> replayRequests(@RequestBody @Valid BatchReplayRequest request) {
        log.info("批量重放请求 - count: {}, targetEnvironment: {}",
                request.getRequestIds().size(), request.getTargetEnvironment());

        return requestReplayService.replayRequests(request.getRequestIds(), request.getTargetEnvironment())
                .collectList()
                .map(results -> {
                    long successCount = results.stream().filter(ReplayResult::isSuccess).count();
                    long failCount = results.size() - successCount;
                    String message = String.format("批量重放完成，成功: %d, 失败: %d", successCount, failCount);
                    return ApiResponse.success(message, results);
                })
                .onErrorResume(e -> {
                    log.error("批量重放失败 - error: {}", e.getMessage());
                    return Mono.just(ApiResponse.error("批量重放失败: " + e.getMessage()));
                });
    }

    /**
     * 清空所有录制记录
     *
     * @return 操作结果
     */
    @DeleteMapping("/requests")
    public Mono<ApiResponse<Void>> clearRecordedRequests() {
        log.info("清空所有录制记录");

        return requestReplayService.clearRecordedRequests()
                .then(Mono.just(ApiResponse.<Void>success("录制记录已清空")))
                .onErrorResume(e -> {
                    log.error("清空录制记录失败 - error: {}", e.getMessage());
                    return Mono.just(ApiResponse.error("清空失败: " + e.getMessage()));
                });
    }

    /**
     * 删除单个录制请求
     *
     * @param id 请求ID
     * @return 操作结果
     */
    @DeleteMapping("/requests/{id}")
    public Mono<ApiResponse<Boolean>> deleteRecordedRequest(@PathVariable String id) {
        log.info("删除录制请求 - id: {}", id);

        return requestReplayService.deleteRecordedRequest(id)
                .map(deleted -> {
                    if (deleted) {
                        return ApiResponse.success("删除成功", true);
                    } else {
                        return ApiResponse.<Boolean>error(404, "请求不存在: " + id);
                    }
                })
                .onErrorResume(e -> {
                    log.error("删除录制请求失败 - id: {}, error: {}", id, e.getMessage());
                    return Mono.just(ApiResponse.error("删除失败: " + e.getMessage()));
                });
    }

    /**
     * 开启/关闭录制请求DTO
     */
    @Data
    public static class EnableRequest {
        /**
         * 是否开启录制
         */
        @NotNull(message = "enabled不能为空")
        private Boolean enabled;
    }

    /**
     * 单个重放请求DTO
     */
    @Data
    public static class ReplaySingleRequest {
        /**
         * 目标环境名称
         * 为空则使用默认环境
         */
        private String targetEnvironment;
    }

    /**
     * 批量重放请求DTO
     */
    @Data
    public static class BatchReplayRequest {
        /**
         * 需要重放的请求ID列表
         */
        @NotEmpty(message = "requestIds不能为空")
        private List<String> requestIds;

        /**
         * 目标环境名称
         * 为空则使用默认环境
         */
        private String targetEnvironment;
    }
}
