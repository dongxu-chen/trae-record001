package com.apigateway.core.replay;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 请求重放配置属性类
 * 用于配置请求录制和重放的各项参数，包括是否开启录制、最大录制数、过期时间、目标环境等
 * 支持基于URL路径和HTTP方法的细粒度录制过滤
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Data
@Component
@ConfigurationProperties(prefix = "gateway.replay")
public class ReplayProperties {

    /**
     * 是否开启请求录制
     * 默认值：false
     */
    private boolean enabled = false;

    /**
     * Redis存储Key前缀
     * 默认值：gateway:replay
     */
    private String keyPrefix = "gateway:replay";

    /**
     * 最大录制请求数
     * 超过此数量后将自动删除最早的录制记录
     * 默认值：1000
     */
    private int maxRecords = 1000;

    /**
     * 录制记录过期时间
     * 默认值：24小时
     */
    private Duration expireTime = Duration.ofHours(24);

    /**
     * 需要录制的HTTP方法列表
     * 为空则录制所有方法
     * 例如：GET, POST, PUT, DELETE
     */
    private List<String> includeMethods = new ArrayList<>();

    /**
     * 不需要录制的HTTP方法列表
     * 优先级高于includeMethods
     * 例如：OPTIONS, HEAD
     */
    private List<String> excludeMethods = new ArrayList<>();

    /**
     * 需要录制的路径模式列表
     * 支持Ant风格路径匹配，例如：/api/rest/**
     * 为空则录制所有路径
     */
    private List<String> includePaths = new ArrayList<>();

    /**
     * 不需要录制的路径模式列表
     * 支持Ant风格路径匹配，例如：/api/rest/auth/**
     * 优先级高于includePaths
     */
    private List<String> excludePaths = new ArrayList<>();

    /**
     * 是否录制请求体
     * 默认值：true
     */
    private boolean recordBody = true;

    /**
     * 请求体最大录制大小（字节）
     * 超过此大小的请求体将被截断
     * 默认值：1MB
     */
    private int maxBodySize = 1024 * 1024;

    /**
     * 是否录制请求头
     * 默认值：true
     */
    private boolean recordHeaders = true;

    /**
     * 需要排除的请求头列表
     * 例如：Authorization, Cookie等敏感信息
     */
    private List<String> excludeHeaders = new ArrayList<>();

    /**
     * 目标环境配置
     * key为环境名称，value为环境基础URL
     * 例如：dev -> http://dev-api.example.com
     *       test -> http://test-api.example.com
     *       prod -> http://api.example.com
     */
    private Map<String, String> environments = new HashMap<>();

    /**
     * 默认目标环境名称
     * 重放时未指定环境时使用
     */
    private String defaultEnvironment;

    /**
     * 重放请求超时时间
     * 默认值：30秒
     */
    private Duration replayTimeout = Duration.ofSeconds(30);

    /**
     * 批量重放最大并发数
     * 默认值：10
     */
    private int maxConcurrentReplays = 10;
}
