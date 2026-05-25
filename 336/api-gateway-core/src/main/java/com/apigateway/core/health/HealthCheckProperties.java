package com.apigateway.core.health;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

/**
 * 健康检查配置属性类
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Data
@Component
@ConfigurationProperties(prefix = "gateway.health-check")
public class HealthCheckProperties {

    /**
     * 全局开关，是否启用健康检查
     */
    private boolean enabled = true;

    /**
     * 探测线程池配置
     */
    private ThreadPoolConfig threadPool = new ThreadPoolConfig();

    /**
     * 告警阈值配置
     */
    private AlertConfig alert = new AlertConfig();

    /**
     * 通知配置
     */
    private NotificationConfig notification = new NotificationConfig();

    /**
     * 监控接口列表
     */
    private List<HealthCheckEndpoint> endpoints = new ArrayList<>();

    /**
     * 历史记录最大保存条数
     */
    private int maxHistorySize = 100;

    /**
     * 线程池配置
     */
    @Data
    public static class ThreadPoolConfig {

        /**
         * 核心线程数
         */
        private int coreSize = 5;

        /**
         * 最大线程数
         */
        private int maxSize = 10;

        /**
         * 队列容量
         */
        private int queueCapacity = 100;

        /**
         * 线程空闲存活时间（秒）
         */
        private int keepAliveSeconds = 60;
    }

    /**
     * 告警阈值配置
     */
    @Data
    public static class AlertConfig {

        /**
         * 连续失败次数阈值，超过则触发告警
         */
        private int consecutiveFailureThreshold = 3;

        /**
         * 降级状态阈值（不健康接口占比，0-1）
         */
        private double degradedThreshold = 0.3;

        /**
         * 不健康状态阈值（不健康接口占比，0-1）
         */
        private double unhealthyThreshold = 0.6;
    }

    /**
     * 通知配置
     */
    @Data
    public static class NotificationConfig {

        /**
         * 是否启用Webhook通知
         */
        private boolean webhookEnabled = false;

        /**
         * Webhook URL
         */
        private String webhookUrl;

        /**
         * 是否启用邮件通知
         */
        private boolean emailEnabled = false;

        /**
         * 邮件收件人列表
         */
        private List<String> emailRecipients = new ArrayList<>();

        /**
         * 通知静默期（毫秒），避免频繁发送通知
         */
        private long silentPeriod = 300000;
    }
}
