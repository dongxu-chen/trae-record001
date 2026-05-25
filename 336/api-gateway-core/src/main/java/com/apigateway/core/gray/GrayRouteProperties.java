package com.apigateway.core.gray;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

/**
 * 灰度路由配置属性类
 * 支持多种灰度规则配置，包括Header、比例、用户ID、IP、路径等
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Data
@Component
@ConfigurationProperties(prefix = "gateway.gray")
public class GrayRouteProperties {

    /**
     * 是否开启灰度路由
     * 默认值：false
     */
    private boolean enabled = false;

    /**
     * v1版本服务地址
     */
    private String v1Uri = "http://localhost:8081";

    /**
     * v2版本服务地址
     */
    private String v2Uri = "http://localhost:8082";

    /**
     * 默认版本，当没有匹配到灰度规则时使用
     */
    private String defaultVersion = "v1";

    /**
     * 是否开启一致性哈希
     * 开启后同一用户/IP始终路由到同一版本
     */
    private boolean consistentHashEnabled = true;

    /**
     * 一致性哈希虚拟节点数
     * 数值越大分布越均匀，占用内存越多
     */
    private int consistentHashVirtualNodes = 160;

    /**
     * 是否开启统计
     */
    private boolean statsEnabled = true;

    /**
     * 灰度规则列表
     * 支持多组灰度规则配置，按权重排序匹配
     */
    private List<GrayRuleConfig> rules = new ArrayList<>();

    /**
     * 灰度规则配置内部类
     */
    @Data
    public static class GrayRuleConfig {

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
        private GrayRule.RuleType type;

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
        private List<String> userIds = new ArrayList<>();

        /**
         * IP地址列表（IP类型使用）
         */
        private List<String> ips = new ArrayList<>();

        /**
         * 路径模式（PATH类型使用）
         */
        private String pathPattern;

        /**
         * 请求方法（PATH类型使用，可选）
         */
        private String method;

        /**
         * 目标版本，v1或v2
         */
        private String targetVersion = "v2";

        /**
         * 权重，数值越大优先级越高
         */
        private Integer weight = 10;

        /**
         * 是否启用
         */
        private boolean enabled = true;

        /**
         * 一致性哈希键配置
         * 可选值：userId, ip, header:X-User-Id
         */
        private String consistentHashKey;
    }
}
