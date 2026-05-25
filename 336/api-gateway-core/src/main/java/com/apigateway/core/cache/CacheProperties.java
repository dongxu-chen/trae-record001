package com.apigateway.core.cache;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/**
 * 缓存配置属性类
 * 用于配置Redis缓存的各项参数，包括是否开启、过期时间、缓存前缀等
 * 支持基于URL路径的细粒度缓存规则配置
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Data
@Component
@ConfigurationProperties(prefix = "gateway.cache")
public class CacheProperties {

    /**
     * 是否开启缓存
     * 默认值：false
     */
    private boolean enabled = false;

    /**
     * 缓存默认过期时间
     * 默认值：5分钟
     */
    private Duration defaultExpireTime = Duration.ofMinutes(5);

    /**
     * 缓存Key前缀
     * 默认值：gateway:cache
     */
    private String keyPrefix = "gateway:cache";

    /**
     * 是否缓存GET请求
     * 默认值：true
     */
    private boolean cacheGetRequests = true;

    /**
     * 缓存规则列表
     * 可针对不同URL路径配置不同的缓存策略
     */
    private List<CacheRule> rules = new ArrayList<>();

    /**
     * 需要排除缓存的路径模式列表
     * 支持Ant风格路径匹配，例如：/api/rest/**
     */
    private List<String> excludePaths = new ArrayList<>();

    /**
     * 缓存最大条目数
     * 默认值：10000
     */
    private int maxEntries = 10000;

    /**
     * 是否开启缓存统计
     * 默认值：false
     */
    private boolean enableStats = false;

    /**
     * 缓存规则内部类
     * 定义针对特定路径的缓存策略
     */
    @Data
    public static class CacheRule {

        /**
         * 路径模式
         * 支持Ant风格路径匹配，例如：/api/rest/users/**
         */
        private String pathPattern;

        /**
         * 该路径的缓存过期时间
         * 不配置则使用默认过期时间
         */
        private Duration expireTime;

        /**
         * 是否开启该路径的缓存
         * 默认值：true
         */
        private boolean enabled = true;

        /**
         * 参与缓存Key生成的查询参数名列表
         * 为空则所有查询参数都参与Key生成
         */
        private List<String> includeQueryParams;

        /**
         * 不参与缓存Key生成的查询参数名列表
         * 优先级高于includeQueryParams
         */
        private List<String> excludeQueryParams;

        /**
         * 是否包含请求头参与Key生成
         * 默认值：false
         */
        private boolean includeHeaders = false;

        /**
         * 参与Key生成的请求头名称列表
         * includeHeaders为true时生效
         */
        private List<String> includeHeadersList;
    }
}
