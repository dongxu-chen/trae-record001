package com.apigateway.core.health;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Scheduler;
import reactor.core.scheduler.Schedulers;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedDeque;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * API巡检核心服务
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ApiHealthCheckService {

    private final HealthCheckProperties properties;

    private WebClient webClient;

    private Scheduler healthCheckScheduler;

    /**
     * 存储每个接口的最新探测结果
     */
    private final Map<String, HealthCheckResult> latestResults = new ConcurrentHashMap<>();

    /**
     * 存储探测历史记录
     */
    private final Deque<HealthCheckResult> healthHistory = new ConcurrentLinkedDeque<>();

    /**
     * 存储每个接口的连续失败次数
     */
    private final Map<String, AtomicInteger> consecutiveFailures = new ConcurrentHashMap<>();

    /**
     * 存储上次通知时间，避免频繁发送通知
     */
    private final Map<String, LocalDateTime> lastNotificationTime = new ConcurrentHashMap<>();

    /**
     * 动态添加的监控接口列表
     */
    private final List<HealthCheckEndpoint> dynamicEndpoints = Collections.synchronizedList(new ArrayList<>());

    /**
     * 初始化服务
     */
    @PostConstruct
    public void init() {
        if (!properties.isEnabled()) {
            log.info("健康检查功能已禁用");
            return;
        }

        HealthCheckProperties.ThreadPoolConfig threadPoolConfig = properties.getThreadPool();
        this.healthCheckScheduler = Schedulers.fromExecutorService(
                Executors.newFixedThreadPool(threadPoolConfig.getCoreSize(),
                        r -> {
                            Thread thread = new Thread(r, "health-check-");
                            thread.setDaemon(true);
                            return thread;
                        })
        );

        this.webClient = WebClient.builder()
                .clientConnector(new ReactorClientHttpConnector())
                .build();

        log.info("API巡检服务初始化完成，监控接口数量: {}", getAllEndpoints().size());
    }

    /**
     * 探测单个接口
     *
     * @param endpoint 接口配置
     * @return 探测结果
     */
    public Mono<HealthCheckResult> checkEndpoint(HealthCheckEndpoint endpoint) {
        if (!endpoint.isEnabled()) {
            log.debug("接口 {} 已禁用，跳过探测", endpoint.getName());
            return Mono.empty();
        }

        long startTime = System.currentTimeMillis();
        LocalDateTime checkTime = LocalDateTime.now();

        return webClient.method(endpoint.getMethod())
                .uri(endpoint.getUrl())
                .retrieve()
                .toBodilessEntity()
                .timeout(endpoint.getTimeout())
                .map(response -> {
                    long responseTime = System.currentTimeMillis() - startTime;
                    int statusCode = response.getStatusCode().value();
                    boolean healthy = statusCode == endpoint.getExpectedStatusCode();

                    return buildResult(endpoint, statusCode, healthy, responseTime, null, checkTime);
                })
                .onErrorResume(error -> {
                    long responseTime = System.currentTimeMillis() - startTime;
                    int statusCode = error instanceof org.springframework.web.reactive.function.client.WebClientResponseException
                            ? ((org.springframework.web.reactive.function.client.WebClientResponseException) error).getStatusCode().value()
                            : 0;

                    return Mono.just(buildResult(endpoint, statusCode, false, responseTime, error.getMessage(), checkTime));
                })
                .doOnNext(result -> {
                    processResult(result, endpoint);
                    log.debug("接口探测完成 - {}: {} - {}, 响应时间: {}ms",
                            endpoint.getName(), result.getUrl(), result.isHealthy() ? "健康" : "不健康", result.getResponseTime());
                })
                .subscribeOn(healthCheckScheduler);
    }

    /**
     * 探测所有配置的接口（并行执行）
     *
     * @return 所有探测结果
     */
    public Flux<HealthCheckResult> checkAllEndpoints() {
        if (!properties.isEnabled()) {
            log.debug("健康检查功能已禁用");
            return Flux.empty();
        }

        List<HealthCheckEndpoint> allEndpoints = getAllEndpoints();
        log.info("开始并行探测 {} 个接口", allEndpoints.size());

        return Flux.fromIterable(allEndpoints)
                .filter(HealthCheckEndpoint::isEnabled)
                .flatMap(this::checkEndpoint)
                .doOnComplete(() -> log.info("所有接口探测完成"));
    }

    /**
     * 获取当前健康状态
     *
     * @return 健康状态
     */
    public Mono<Map<String, Object>> getHealthStatus() {
        return Mono.fromCallable(() -> {
            Map<String, Object> statusMap = new LinkedHashMap<>();
            List<HealthCheckEndpoint> allEndpoints = getAllEndpoints();
            int totalEndpoints = (int) allEndpoints.stream().filter(HealthCheckEndpoint::isEnabled).count();

            if (totalEndpoints == 0) {
                statusMap.put("status", HealthStatus.HEALTHY);
                statusMap.put("totalEndpoints", 0);
                statusMap.put("healthyEndpoints", 0);
                statusMap.put("unhealthyEndpoints", 0);
                statusMap.put("checkTime", LocalDateTime.now());
                return statusMap;
            }

            long healthyCount = latestResults.values().stream()
                    .filter(HealthCheckResult::isHealthy)
                    .count();
            long unhealthyCount = totalEndpoints - healthyCount;
            double unhealthyRatio = (double) unhealthyCount / totalEndpoints;

            HealthStatus status;
            if (unhealthyRatio >= properties.getAlert().getUnhealthyThreshold()) {
                status = HealthStatus.UNHEALTHY;
            } else if (unhealthyRatio >= properties.getAlert().getDegradedThreshold()) {
                status = HealthStatus.DEGRADED;
            } else {
                status = HealthStatus.HEALTHY;
            }

            statusMap.put("status", status);
            statusMap.put("totalEndpoints", totalEndpoints);
            statusMap.put("healthyEndpoints", healthyCount);
            statusMap.put("unhealthyEndpoints", unhealthyCount);
            statusMap.put("unhealthyRatio", String.format("%.2f%%", unhealthyRatio * 100));
            statusMap.put("latestResults", new ArrayList<>(latestResults.values()));
            statusMap.put("checkTime", LocalDateTime.now());

            return statusMap;
        }).subscribeOn(healthCheckScheduler);
    }

    /**
     * 获取历史探测记录
     *
     * @param limit 返回记录数量限制
     * @return 历史记录列表
     */
    public Mono<List<HealthCheckResult>> getHealthHistory(int limit) {
        return Mono.fromCallable(() -> {
            List<HealthCheckResult> history = new ArrayList<>(healthHistory);
            if (limit > 0 && limit < history.size()) {
                return history.subList(0, limit);
            }
            return history;
        }).subscribeOn(healthCheckScheduler);
    }

    /**
     * 获取所有历史探测记录
     *
     * @return 历史记录列表
     */
    public Mono<List<HealthCheckResult>> getHealthHistory() {
        return getHealthHistory(0);
    }

    /**
     * 失败通知
     *
     * @param result 探测结果
     */
    public void notifyOnFailure(HealthCheckResult result) {
        HealthCheckProperties.NotificationConfig notificationConfig = properties.getNotification();
        String endpointName = result.getEndpointName();

        LocalDateTime lastNotify = lastNotificationTime.get(endpointName);
        if (lastNotify != null &&
                Duration.between(lastNotify, LocalDateTime.now()).toMillis() < notificationConfig.getSilentPeriod()) {
            log.debug("接口 {} 处于通知静默期，跳过通知", endpointName);
            return;
        }

        if (notificationConfig.isWebhookEnabled() && notificationConfig.getWebhookUrl() != null) {
            sendWebhookNotification(result, notificationConfig.getWebhookUrl())
                    .doOnSuccess(v -> {
                        lastNotificationTime.put(endpointName, LocalDateTime.now());
                        log.info("Webhook通知已发送 - 接口: {}", endpointName);
                    })
                    .doOnError(e -> log.error("Webhook通知发送失败 - 接口: {}", endpointName, e))
                    .subscribe();
        }

        if (notificationConfig.isEmailEnabled() && !notificationConfig.getEmailRecipients().isEmpty()) {
            sendEmailNotification(result, notificationConfig.getEmailRecipients())
                    .doOnSuccess(v -> {
                        lastNotificationTime.put(endpointName, LocalDateTime.now());
                        log.info("邮件通知已发送 - 接口: {}", endpointName);
                    })
                    .doOnError(e -> log.error("邮件通知发送失败 - 接口: {}", endpointName, e))
                    .subscribe();
        }
    }

    /**
     * 获取所有监控接口列表（配置 + 动态添加）
     *
     * @return 接口列表
     */
    public List<HealthCheckEndpoint> getAllEndpoints() {
        List<HealthCheckEndpoint> allEndpoints = new ArrayList<>();
        allEndpoints.addAll(properties.getEndpoints());
        allEndpoints.addAll(dynamicEndpoints);
        return allEndpoints;
    }

    /**
     * 动态添加监控接口
     *
     * @param endpoint 接口配置
     */
    public void addEndpoint(HealthCheckEndpoint endpoint) {
        dynamicEndpoints.add(endpoint);
        log.info("已添加监控接口: {} - {}", endpoint.getName(), endpoint.getUrl());
    }

    /**
     * 构建探测结果
     */
    private HealthCheckResult buildResult(HealthCheckEndpoint endpoint, int statusCode, boolean healthy,
                                           long responseTime, String errorMessage, LocalDateTime checkTime) {
        return HealthCheckResult.builder()
                .endpointName(endpoint.getName())
                .url(endpoint.getUrl())
                .statusCode(statusCode)
                .healthy(healthy)
                .responseTime(responseTime)
                .errorMessage(errorMessage)
                .checkTime(checkTime)
                .build();
    }

    /**
     * 处理探测结果
     */
    private void processResult(HealthCheckResult result, HealthCheckEndpoint endpoint) {
        latestResults.put(result.getEndpointName(), result);
        addToHistory(result);

        AtomicInteger failureCount = consecutiveFailures.computeIfAbsent(
                result.getEndpointName(), k -> new AtomicInteger(0));

        if (!result.isHealthy()) {
            int currentFailures = failureCount.incrementAndGet();
            log.warn("接口 {} 探测失败，连续失败次数: {}", result.getEndpointName(), currentFailures);

            if (currentFailures >= properties.getAlert().getConsecutiveFailureThreshold()) {
                log.error("接口 {} 连续失败次数超过阈值 {}，触发告警",
                        result.getEndpointName(), properties.getAlert().getConsecutiveFailureThreshold());
                notifyOnFailure(result);
            }
        } else {
            if (failureCount.get() > 0) {
                log.info("接口 {} 恢复正常，连续失败次数已重置", result.getEndpointName());
            }
            failureCount.set(0);
        }
    }

    /**
     * 添加到历史记录
     */
    private void addToHistory(HealthCheckResult result) {
        healthHistory.addFirst(result);
        while (healthHistory.size() > properties.getMaxHistorySize()) {
            healthHistory.removeLast();
        }
    }

    /**
     * 发送Webhook通知
     */
    private Mono<Void> sendWebhookNotification(HealthCheckResult result, String webhookUrl) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("type", "HEALTH_CHECK_FAILURE");
        payload.put("timestamp", LocalDateTime.now().toString());
        payload.put("endpoint", result.getEndpointName());
        payload.put("url", result.getUrl());
        payload.put("statusCode", result.getStatusCode());
        payload.put("responseTime", result.getResponseTime());
        payload.put("errorMessage", result.getErrorMessage());

        return webClient.post()
                .uri(webhookUrl)
                .bodyValue(payload)
                .retrieve()
                .toBodilessEntity()
                .then()
                .doOnError(e -> log.error("发送Webhook通知失败: {}", e.getMessage()));
    }

    /**
     * 发送邮件通知
     */
    private Mono<Void> sendEmailNotification(HealthCheckResult result, List<String> recipients) {
        log.info("发送邮件通知给: {}，内容: 接口 {} 探测失败", recipients, result.getEndpointName());
        return Mono.empty();
    }
}
