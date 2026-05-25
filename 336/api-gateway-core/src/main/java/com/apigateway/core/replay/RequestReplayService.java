package com.apigateway.core.replay;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RListReactive;
import org.redisson.api.RMapCacheReactive;
import org.redisson.api.RedissonReactiveClient;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

/**
 * 请求重放服务类
 * 提供请求录制、重放、查询、清空等核心功能
 * 使用Redisson响应式客户端存储录制数据，采用响应式编程风格
 * 支持多环境重放配置和按路径、方法过滤录制
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class RequestReplayService {

    /**
     * Redisson响应式客户端
     */
    private final RedissonReactiveClient redissonReactiveClient;

    /**
     * 重放配置属性
     */
    private final ReplayProperties replayProperties;

    /**
     * WebClient用于发送重放请求
     */
    private final WebClient.Builder webClientBuilder;

    /**
     * 路径匹配器
     */
    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    /**
     * 录制请求Map的缓存名称
     */
    private static final String REQUESTS_MAP_NAME = "replay:requests";

    /**
     * 录制请求ID列表的缓存名称
     */
    private static final String REQUEST_IDS_LIST_NAME = "replay:requestIds";

    /**
     * 录制请求
     * 将符合条件的请求信息录制到Redis中
     *
     * @param recordedRequest 录制的请求信息
     * @return 操作结果Mono
     */
    public Mono<Void> recordRequest(RecordedRequest recordedRequest) {
        if (!replayProperties.isEnabled()) {
            log.debug("请求录制未启用，跳过录制 - requestId: {}", recordedRequest.getRequestId());
            return Mono.empty();
        }

        if (!shouldRecord(recordedRequest.getMethod(), recordedRequest.getPath())) {
            log.debug("请求不符合录制条件，跳过录制 - method: {}, path: {}",
                    recordedRequest.getMethod(), recordedRequest.getPath());
            return Mono.empty();
        }

        String fullKey = buildFullKey(recordedRequest.getRequestId());
        log.debug("开始录制请求 - requestId: {}, key: {}, method: {}, path: {}",
                recordedRequest.getRequestId(), fullKey, recordedRequest.getMethod(), recordedRequest.getPath());

        return getRequestsMap()
                .put(fullKey, recordedRequest, replayProperties.getExpireTime().toMillis(), TimeUnit.MILLISECONDS)
                .then(getRequestIdsList())
                .flatMap(list -> list.add(recordedRequest.getRequestId()))
                .then(trimExcessRecords())
                .doOnSuccess(v -> log.info("请求录制成功 - requestId: {}, method: {}, path: {}",
                        recordedRequest.getRequestId(), recordedRequest.getMethod(), recordedRequest.getPath()))
                .doOnError(e -> log.error("请求录制失败 - requestId: {}, error: {}",
                        recordedRequest.getRequestId(), e.getMessage()))
                .onErrorResume(e -> Mono.empty());
    }

    /**
     * 重放单个请求到指定环境
     *
     * @param requestId           请求ID
     * @param targetEnvironment   目标环境名称
     * @return 重放结果Mono
     */
    public Mono<ReplayResult> replayRequest(String requestId, String targetEnvironment) {
        log.info("开始重放请求 - requestId: {}, targetEnvironment: {}", requestId, targetEnvironment);

        return getRecordedRequest(requestId)
                .switchIfEmpty(Mono.error(new IllegalArgumentException("请求不存在: " + requestId)))
                .flatMap(requested -> doReplay(requested, targetEnvironment))
                .doOnSuccess(result -> log.info("请求重放完成 - requestId: {}, success: {}, statusCode: {}",
                        requestId, result.isSuccess(), result.getStatusCode()))
                .doOnError(e -> log.error("请求重放失败 - requestId: {}, error: {}", requestId, e.getMessage()));
    }

    /**
     * 批量重放请求
     *
     * @param requestIds        请求ID列表
     * @param targetEnvironment 目标环境名称
     * @return 重放结果Flux
     */
    public Flux<ReplayResult> replayRequests(List<String> requestIds, String targetEnvironment) {
        log.info("开始批量重放请求 - count: {}, targetEnvironment: {}", requestIds.size(), targetEnvironment);

        return Flux.fromIterable(requestIds)
                .flatMap(requestId -> replayRequest(requestId, targetEnvironment)
                                .subscribeOn(Schedulers.parallel()),
                        replayProperties.getMaxConcurrentReplays())
                .doOnComplete(() -> log.info("批量重放完成 - count: {}", requestIds.size()));
    }

    /**
     * 查询录制的请求列表
     *
     * @param pageNum  页码（从0开始）
     * @param pageSize 每页大小
     * @return 录制请求列表Mono（包含总记录数和当前页数据）
     */
    public Mono<Map<String, Object>> getRecordedRequests(int pageNum, int pageSize) {
        log.debug("查询录制请求列表 - pageNum: {}, pageSize: {}", pageNum, pageSize);

        return getRequestIdsList()
                .flatMap(list -> list.size()
                        .flatMap(total -> {
                            int from = Math.max(0, pageNum * pageSize);
                            int to = Math.min((pageNum + 1) * pageSize - 1, total.intValue() - 1);

                            if (from > to || total == 0) {
                                return Mono.just(Map.of(
                                        "total", 0,
                                        "pageNum", pageNum,
                                        "pageSize", pageSize,
                                        "list", Collections.emptyList()
                                ));
                            }

                            return list.range(from, to)
                                    .collectList()
                                    .flatMap(ids -> Flux.fromIterable(ids)
                                            .flatMap(id -> getRecordedRequest(id))
                                            .collectList()
                                            .map(requests -> Map.of(
                                                    "total", total,
                                                    "pageNum", pageNum,
                                                    "pageSize", pageSize,
                                                    "list", requests.stream()
                                                            .sorted(Comparator.comparing(RecordedRequest::getTimestamp).reversed())
                                                            .collect(Collectors.toList())
                                            )));
                        }))
                .doOnError(e -> log.error("查询录制请求列表失败 - error: {}", e.getMessage()));
    }

    /**
     * 查询所有录制的请求
     *
     * @return 录制请求列表Flux
     */
    public Flux<RecordedRequest> getAllRecordedRequests() {
        return getRequestIdsList()
                .flatMapMany(RListReactive::readAll)
                .flatMap(this::getRecordedRequest)
                .sort(Comparator.comparing(RecordedRequest::getTimestamp).reversed());
    }

    /**
     * 根据ID获取单个录制请求
     *
     * @param requestId 请求ID
     * @return 录制请求Mono
     */
    public Mono<RecordedRequest> getRecordedRequest(String requestId) {
        String fullKey = buildFullKey(requestId);
        return getRequestsMap()
                .<RecordedRequest>get(fullKey)
                .doOnError(e -> log.error("获取录制请求失败 - requestId: {}, error: {}", requestId, e.getMessage()));
    }

    /**
     * 清空所有录制记录
     *
     * @return 操作结果Mono
     */
    public Mono<Void> clearRecordedRequests() {
        log.info("清空所有录制记录");

        return Mono.zip(
                        getRequestsMap().clear(),
                        getRequestIdsList().delete()
                )
                .doOnSuccess(v -> log.info("录制记录清空成功"))
                .doOnError(e -> log.error("清空录制记录失败 - error: {}", e.getMessage()))
                .then();
    }

    /**
     * 删除单个录制请求
     *
     * @param requestId 请求ID
     * @return 操作结果Mono
     */
    public Mono<Boolean> deleteRecordedRequest(String requestId) {
        log.info("删除录制请求 - requestId: {}", requestId);

        String fullKey = buildFullKey(requestId);
        return Mono.zip(
                        getRequestsMap().remove(fullKey),
                        getRequestIdsList().flatMap(list -> list.remove(requestId))
                )
                .map(tuple -> tuple.getT1() != null || tuple.getT2())
                .doOnSuccess(result -> log.info("删除录制请求结果 - requestId: {}, result: {}", requestId, result))
                .doOnError(e -> log.error("删除录制请求失败 - requestId: {}, error: {}", requestId, e.getMessage()));
    }

    /**
     * 开启/关闭录制功能
     *
     * @param enabled 是否开启
     */
    public void setRecordingEnabled(boolean enabled) {
        replayProperties.setEnabled(enabled);
        log.info("请求录制功能已{}", enabled ? "开启" : "关闭");
    }

    /**
     * 检查录制功能是否开启
     *
     * @return 是否开启
     */
    public boolean isRecordingEnabled() {
        return replayProperties.isEnabled();
    }

    /**
     * 获取所有目标环境配置
     *
     * @return 环境配置Map
     */
    public Map<String, String> getEnvironments() {
        return replayProperties.getEnvironments();
    }

    /**
     * 判断请求是否应该被录制
     *
     * @param method HTTP方法
     * @param path   请求路径
     * @return 是否应该录制
     */
    public boolean shouldRecord(String method, String path) {
        List<String> excludeMethods = replayProperties.getExcludeMethods();
        if (!excludeMethods.isEmpty() && excludeMethods.contains(method.toUpperCase())) {
            return false;
        }

        List<String> includeMethods = replayProperties.getIncludeMethods();
        if (!includeMethods.isEmpty() && !includeMethods.contains(method.toUpperCase())) {
            return false;
        }

        List<String> excludePaths = replayProperties.getExcludePaths();
        for (String pattern : excludePaths) {
            if (pathMatcher.match(pattern, path)) {
                return false;
            }
        }

        List<String> includePaths = replayProperties.getIncludePaths();
        if (!includePaths.isEmpty()) {
            for (String pattern : includePaths) {
                if (pathMatcher.match(pattern, path)) {
                    return true;
                }
            }
            return false;
        }

        return true;
    }

    /**
     * 执行实际的重放操作
     *
     * @param recordedRequest   录制的请求
     * @param targetEnvironment 目标环境名称
     * @return 重放结果Mono
     */
    private Mono<ReplayResult> doReplay(RecordedRequest recordedRequest, String targetEnvironment) {
        String targetBaseUrl = getTargetBaseUrl(targetEnvironment);
        if (targetBaseUrl == null) {
            return Mono.just(buildErrorResult(recordedRequest.getRequestId(), targetEnvironment,
                    "目标环境不存在: " + targetEnvironment));
        }

        String targetUrl = buildTargetUrl(targetBaseUrl, recordedRequest.getPath(), recordedRequest.getQueryParams());
        HttpMethod httpMethod = HttpMethod.valueOf(recordedRequest.getMethod());

        WebClient.RequestHeadersSpec<?> requestSpec = webClientBuilder.build()
                .method(httpMethod)
                .uri(targetUrl)
                .headers(headers -> {
                    if (replayProperties.isRecordHeaders() && recordedRequest.getHeaders() != null) {
                        recordedRequest.getHeaders().forEach((key, value) -> {
                            if (!replayProperties.getExcludeHeaders().contains(key)) {
                                headers.add(key, value);
                            }
                        });
                    }
                    headers.remove(HttpHeaders.CONTENT_LENGTH);
                });

        if (recordedRequest.getBody() != null && !recordedRequest.getBody().isEmpty()
                && httpMethod != HttpMethod.GET && httpMethod != HttpMethod.HEAD) {
            ((WebClient.RequestBodySpec) requestSpec).contentType(MediaType.APPLICATION_JSON);
            ((WebClient.RequestBodySpec) requestSpec).body(BodyInserters.fromValue(recordedRequest.getBody()));
        }

        long startTime = System.currentTimeMillis();

        return requestSpec
                .exchange()
                .timeout(replayProperties.getReplayTimeout())
                .flatMap(response -> {
                    long responseTime = System.currentTimeMillis() - startTime;
                    return response.toEntity(String.class)
                            .map(entity -> buildSuccessResult(recordedRequest, targetEnvironment,
                                    targetUrl, entity, responseTime));
                })
                .onErrorResume(e -> Mono.just(buildErrorResult(recordedRequest.getRequestId(),
                        targetEnvironment, targetUrl, e.getMessage(), recordedRequest.getResponseStatus())));
    }

    /**
     * 获取目标环境的基础URL
     *
     * @param targetEnvironment 目标环境名称
     * @return 基础URL
     */
    private String getTargetBaseUrl(String targetEnvironment) {
        if (targetEnvironment == null || targetEnvironment.isEmpty()) {
            targetEnvironment = replayProperties.getDefaultEnvironment();
        }
        return replayProperties.getEnvironments().get(targetEnvironment);
    }

    /**
     * 构建目标URL
     *
     * @param baseUrl     基础URL
     * @param path        请求路径
     * @param queryParams 查询参数
     * @return 完整URL
     */
    private String buildTargetUrl(String baseUrl, String path, Map<String, String[]> queryParams) {
        StringBuilder url = new StringBuilder(baseUrl);
        if (!baseUrl.endsWith("/") && !path.startsWith("/")) {
            url.append("/");
        }
        url.append(path.startsWith("/") ? path.substring(1) : path);

        if (queryParams != null && !queryParams.isEmpty()) {
            url.append("?");
            boolean first = true;
            for (Map.Entry<String, String[]> entry : queryParams.entrySet()) {
                for (String value : entry.getValue()) {
                    if (!first) {
                        url.append("&");
                    }
                    url.append(entry.getKey()).append("=").append(value);
                    first = false;
                }
            }
        }

        return url.toString();
    }

    /**
     * 构建成功的重放结果
     *
     * @param recordedRequest   录制的请求
     * @param targetEnvironment 目标环境
     * @param targetUrl         目标URL
     * @param response          响应实体
     * @param responseTime      响应时间
     * @return 重放结果
     */
    private ReplayResult buildSuccessResult(RecordedRequest recordedRequest, String targetEnvironment,
                                            String targetUrl, ResponseEntity<String> response, long responseTime) {
        Map<String, String> responseHeaders = new HashMap<>();
        response.getHeaders().forEach((key, values) ->
                responseHeaders.put(key, String.join(",", values)));

        Integer originalStatus = recordedRequest.getResponseStatus();
        Integer currentStatus = response.getStatusCode().value();

        return ReplayResult.builder()
                .resultId(UUID.randomUUID().toString())
                .requestId(recordedRequest.getRequestId())
                .targetEnvironment(targetEnvironment)
                .targetUrl(targetUrl)
                .statusCode(currentStatus)
                .responseTime(responseTime)
                .responseBody(response.getBody())
                .responseHeaders(responseHeaders)
                .success(true)
                .replayTime(Instant.now())
                .originalStatusCode(originalStatus)
                .statusMatched(originalStatus == null || originalStatus.equals(currentStatus))
                .build();
    }

    /**
     * 构建错误的重放结果
     *
     * @param requestId         请求ID
     * @param targetEnvironment 目标环境
     * @param errorMessage      错误信息
     * @return 重放结果
     */
    private ReplayResult buildErrorResult(String requestId, String targetEnvironment, String errorMessage) {
        return buildErrorResult(requestId, targetEnvironment, null, errorMessage, null);
    }

    /**
     * 构建错误的重放结果
     *
     * @param requestId         请求ID
     * @param targetEnvironment 目标环境
     * @param targetUrl         目标URL
     * @param errorMessage      错误信息
     * @param originalStatus    原始状态码
     * @return 重放结果
     */
    private ReplayResult buildErrorResult(String requestId, String targetEnvironment, String targetUrl,
                                          String errorMessage, Integer originalStatus) {
        return ReplayResult.builder()
                .resultId(UUID.randomUUID().toString())
                .requestId(requestId)
                .targetEnvironment(targetEnvironment)
                .targetUrl(targetUrl)
                .errorMessage(errorMessage)
                .success(false)
                .replayTime(Instant.now())
                .originalStatusCode(originalStatus)
                .statusMatched(false)
                .build();
    }

    /**
     * 裁剪超出最大数量的录制记录
     *
     * @return 操作结果Mono
     */
    private Mono<Void> trimExcessRecords() {
        int maxRecords = replayProperties.getMaxRecords();
        return getRequestIdsList()
                .flatMap(list -> list.size()
                        .flatMap(size -> {
                            if (size > maxRecords) {
                                int excess = size - maxRecords;
                                log.debug("裁剪超出的录制记录 - current: {}, max: {}, excess: {}",
                                        size, maxRecords, excess);

                                return list.range(0, excess - 1)
                                        .collectList()
                                        .flatMap(excessIds -> {
                                            RMapCacheReactive<String, RecordedRequest> requestsMap = getRequestsMap();
                                            return Flux.fromIterable(excessIds)
                                                    .flatMap(id -> requestsMap.remove(buildFullKey(id)))
                                                    .then(list.removeRange(0, excess));
                                        });
                            }
                            return Mono.empty();
                        }))
                .then();
    }

    /**
     * 构建完整的存储Key
     *
     * @param key 原始Key
     * @return 带前缀的完整Key
     */
    private String buildFullKey(String key) {
        return replayProperties.getKeyPrefix() + ":" + key;
    }

    /**
     * 获取录制请求Map
     *
     * @return RMapCacheReactive实例
     */
    private RMapCacheReactive<String, RecordedRequest> getRequestsMap() {
        return redissonReactiveClient.getMapCache(REQUESTS_MAP_NAME);
    }

    /**
     * 获取录制请求ID列表
     *
     * @return RListReactive实例
     */
    private RListReactive<String> getRequestIdsList() {
        return redissonReactiveClient.getList(REQUEST_IDS_LIST_NAME);
    }
}
