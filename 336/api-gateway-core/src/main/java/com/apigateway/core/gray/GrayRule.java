package com.apigateway.core.gray;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 灰度规则实体类
 * 定义灰度发布的路由规则，支持多种匹配方式
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class GrayRule implements Serializable {

    /**
     * 规则ID
     */
    private String id;

    /**
     * 规则名称
     */
    private String name;

    /**
     * 规则类型
     * HEADER: 按请求头灰度
     * RATIO: 按比例灰度
     * USER_ID: 按用户ID灰度
     * IP: 按IP地址灰度
     * PATH: 按路径灰度
     */
    private RuleType type;

    /**
     * 规则条件
     * 根据不同类型存储不同条件：
     * - HEADER: {"headerName": "X-Gray-User", "headerValue": "true"}
     * - RATIO: {"ratio": "10"} 表示10%流量
     * - USER_ID: {"userIds": ["1001", "1002"]}
     * - IP: {"ips": ["192.168.1.100", "192.168.1.101"]}
     * - PATH: {"pathPattern": "/api/**", "method": "GET"}
     */
    private RuleCondition condition;

    /**
     * 目标版本，如v1、v2
     */
    private String targetVersion;

    /**
     * 目标服务地址，如http://localhost:8081
     */
    private String targetUri;

    /**
     * 权重，用于多规则匹配时的优先级，数值越大优先级越高
     */
    private Integer weight;

    /**
     * 规则状态：ENABLE-启用，DISABLE-禁用
     */
    private RuleStatus status;

    /**
     * 创建时间
     */
    private LocalDateTime createTime;

    /**
     * 更新时间
     */
    private LocalDateTime updateTime;

    /**
     * 规则类型枚举
     */
    public enum RuleType {
        /**
         * 按请求头灰度
         */
        HEADER,
        /**
         * 按比例灰度
         */
        RATIO,
        /**
         * 按用户ID灰度
         */
        USER_ID,
        /**
         * 按IP地址灰度
         */
        IP,
        /**
         * 按路径灰度
         */
        PATH
    }

    /**
     * 规则状态枚举
     */
    public enum RuleStatus {
        /**
         * 启用
         */
        ENABLE,
        /**
         * 禁用
         */
        DISABLE
    }

    /**
     * 规则条件内部类
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RuleCondition implements Serializable {

        /**
         * 请求头名称（HEADER类型使用）
         */
        private String headerName;

        /**
         * 请求头值（HEADER类型使用）
         */
        private String headerValue;

        /**
         * 灰度比例，0-100（RATIO类型使用）
         */
        private Integer ratio;

        /**
         * 用户ID列表（USER_ID类型使用）
         */
        private List<String> userIds;

        /**
         * IP地址列表（IP类型使用）
         */
        private List<String> ips;

        /**
         * 路径模式（PATH类型使用）
         */
        private String pathPattern;

        /**
         * 请求方法（PATH类型使用，可选）
         */
        private String method;

        /**
         * 一致性哈希键，用于保证同一用户始终路由到同一版本
         * 可选值：userId, ip, header:X-User-Id
         */
        private String consistentHashKey;
    }
}
