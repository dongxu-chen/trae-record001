package com.apigateway.core.health;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 健康检查定时调度器
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class HealthCheckScheduler {

    private final ApiHealthCheckService healthCheckService;

    private final HealthCheckProperties properties;

    /**
     * 定时执行健康检查
     * 默认每30秒执行一次，可通过配置修改
     */
    @Scheduled(fixedDelayString = "${gateway.health-check.check-interval:30000}")
    public void scheduledHealthCheck() {
        if (!properties.isEnabled()) {
            log.debug("健康检查功能已禁用，跳过定时巡检");
            return;
        }

        log.debug("开始执行定时健康检查");
        healthCheckService.checkAllEndpoints()
                .doOnComplete(() -> log.debug("定时健康检查执行完成"))
                .doOnError(error -> log.error("定时健康检查执行失败", error))
                .subscribe();
    }
}
