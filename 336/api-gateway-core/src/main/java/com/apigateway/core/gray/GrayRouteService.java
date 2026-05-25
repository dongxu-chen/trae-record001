package com.apigateway.core.gray;

import jakarta.annotation.PostConstruct;
import lombok.Getter;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Service;
import org.springframework.util.AntPathMatcher;
import org.springframework.util.StringUtils;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicReference;
import java.util.stream.Collectors;

/**
 * 灰度路由服务
 * 提供灰度规则匹配、版本选择、统计等核心功能
 * 支持规则热更新，使用ConcurrentHashMap保证线程安全
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class GrayRouteService {

    private final GrayRouteProperties properties;

    /**
     * 灰度规则映射表，key为规则ID，支持热更新
     */
    @Getter
    private final ConcurrentHashMap<String, GrayRule> ruleMap = new ConcurrentHashMap<>();

    /**
     * 灰度统计
     */
    @Getter
    private final GrayStats grayStats = new GrayStats();

    /**
     * 路径匹配器
     */
    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    /**
     * 一致性哈希环（虚拟节点）
     * key: 哈希值, value: 版本(v1/v2)
     */
    private final TreeMap<Long, String> consistentHashRing = new TreeMap<>();

    /**
     * 当前规则版本号，用于检测配置变更
     */
    private final AtomicReference<Long> ruleVersion = new AtomicReference<>(0L);

    /**
     * 初始化灰度路由服务
     * 从配置文件加载初始灰度规则
     */
    @PostConstruct
    public void init() {
        loadRulesFromProperties();
        if (properties.isConsistentHashEnabled()) {
            initConsistentHashRing();
        }
        log.info("灰度路由服务初始化完成，启用状态: {}, 规则数量: {}", properties.isEnabled(), ruleMap.size());
    }

    /**
     * 从配置属性加载灰度规则
     */
    private void loadRulesFromProperties() {
        List<GrayRouteProperties.GrayRuleConfig> configRules = properties.getRules();
        if (configRules != null && !configRules.isEmpty()) {
            for (GrayRouteProperties.GrayRuleConfig config : configRules) {
                GrayRule rule = convertToGrayRule(config);
                ruleMap.put(rule.getId(), rule);
            }
        }
        ruleVersion.incrementAndGet();
    }

    /**
     * 初始化一致性哈希环
     */
    private void initConsistentHashRing() {
        consistentHashRing.clear();
        int virtualNodes = properties.getConsistentHashVirtualNodes();
        
        // 为v1和v2版本分配虚拟节点
        String[] versions = {"v1", "v2"};
        for (String version : versions) {
            for (int i = 0; i < virtualNodes / 2; i++) {
                String key = version + "-" + i;
                long hash = hash(key);
                consistentHashRing.put(hash, version);
            }
        }
        log.info("一致性哈希环初始化完成，虚拟节点数: {}", consistentHashRing.size());
    }

    /**
     * 将配置转换为GrayRule对象
     *
     * @param config 配置对象
     * @return GrayRule对象
     */
    private GrayRule convertToGrayRule(GrayRouteProperties.GrayRuleConfig config) {
        GrayRule.RuleCondition condition = GrayRule.RuleCondition.builder()
                .headerName(config.getHeaderName())
                .headerValue(config.getHeaderValue())
                .ratio(config.getRatio())
                .userIds(config.getUserIds())
                .ips(config.getIps())
                .pathPattern(config.getPathPattern())
                .method(config.getMethod())
                .consistentHashKey(config.getConsistentHashKey())
                .build();

        String targetUri = "v2".equals(config.getTargetVersion()) ? properties.getV2Uri() : properties.getV1Uri();

        return GrayRule.builder()
                .id(config.getId() != null ? config.getId() : UUID.randomUUID().toString())
                .name(config.getName())
                .type(config.getType())
                .condition(condition)
                .targetVersion(config.getTargetVersion())
                .targetUri(targetUri)
                .weight(config.getWeight())
                .status(config.isEnabled() ? GrayRule.RuleStatus.ENABLE : GrayRule.RuleStatus.DISABLE)
                .createTime(LocalDateTime.now())
                .updateTime(LocalDateTime.now())
                .build();
    }

    /**
     * 判断请求是否符合灰度条件
     *
     * @param request 请求对象
     * @return 符合灰度条件返回true，否则返回false
     */
    public boolean isEligibleForGray(ServerHttpRequest request) {
        if (!properties.isEnabled()) {
            return false;
        }

        List<GrayRule> sortedRules = getSortedRules();
        for (GrayRule rule : sortedRules) {
            if (matchRule(request, rule)) {
                return true;
            }
        }
        return false;
    }

    /**
     * 选择路由版本
     * 根据匹配的灰度规则决定路由到v1还是v2
     *
     * @param request 请求对象
     * @return 路由版本信息，包含版本号和目标URI
     */
    public RouteVersion selectRouteVersion(ServerHttpRequest request) {
        if (!properties.isEnabled()) {
            return RouteVersion.builder()
                    .version(properties.getDefaultVersion())
                    .uri(getUriByVersion(properties.getDefaultVersion()))
                    .matched(false)
                    .build();
        }

        List<GrayRule> sortedRules = getSortedRules();
        for (GrayRule rule : sortedRules) {
            if (matchRule(request, rule)) {
                String version = rule.getTargetVersion();
                
                // 一致性哈希：如果开启且配置了哈希键，则使用哈希确定版本
                if (properties.isConsistentHashEnabled() && rule.getCondition().getConsistentHashKey() != null) {
                    String hashKey = getConsistentHashKey(request, rule.getCondition().getConsistentHashKey());
                    if (hashKey != null) {
                        version = getVersionByConsistentHash(hashKey, rule.getCondition().getRatio());
                    }
                }
                
                log.debug("灰度规则匹配成功: 规则ID={}, 规则名称={}, 目标版本={}", 
                        rule.getId(), rule.getName(), version);
                
                return RouteVersion.builder()
                        .version(version)
                        .uri(getUriByVersion(version))
                        .matched(true)
                        .matchedRuleId(rule.getId())
                        .matchedRuleName(rule.getName())
                        .build();
            }
        }

        // 没有匹配到规则，使用默认版本
        return RouteVersion.builder()
                .version(properties.getDefaultVersion())
                .uri(getUriByVersion(properties.getDefaultVersion()))
                .matched(false)
                .build();
    }

    /**
     * 获取按权重排序的规则列表
     *
     * @return 排序后的规则列表
     */
    private List<GrayRule> getSortedRules() {
        return ruleMap.values().stream()
                .filter(rule -> GrayRule.RuleStatus.ENABLE.equals(rule.getStatus()))
                .sorted(Comparator.comparing(GrayRule::getWeight).reversed())
                .collect(Collectors.toList());
    }

    /**
     * 匹配单个规则
     *
     * @param request 请求对象
     * @param rule    灰度规则
     * @return 匹配成功返回true
     */
    private boolean matchRule(ServerHttpRequest request, GrayRule rule) {
        if (rule.getType() == null || rule.getCondition() == null) {
            return false;
        }

        return switch (rule.getType()) {
            case HEADER -> matchHeaderRule(request, rule.getCondition());
            case RATIO -> matchRatioRule(request, rule.getCondition());
            case USER_ID -> matchUserIdRule(request, rule.getCondition());
            case IP -> matchIpRule(request, rule.getCondition());
            case PATH -> matchPathRule(request, rule.getCondition());
        };
    }

    /**
     * 匹配Header规则
     */
    private boolean matchHeaderRule(ServerHttpRequest request, GrayRule.RuleCondition condition) {
        String headerName = condition.getHeaderName();
        String expectedValue = condition.getHeaderValue();
        if (!StringUtils.hasText(headerName)) {
            return false;
        }
        String actualValue = request.getHeaders().getFirst(headerName);
        return expectedValue == null || expectedValue.equals(actualValue);
    }

    /**
     * 匹配比例规则
     */
    private boolean matchRatioRule(ServerHttpRequest request, GrayRule.RuleCondition condition) {
        Integer ratio = condition.getRatio();
        if (ratio == null || ratio <= 0) {
            return false;
        }
        if (ratio >= 100) {
            return true;
        }

        // 使用一致性哈希键或随机数来确定比例
        String hashKey = getConsistentHashKey(request, condition.getConsistentHashKey());
        int value;
        if (hashKey != null) {
            value = Math.abs(hash(hashKey) % 100);
        } else {
            value = new Random().nextInt(100);
        }
        return value < ratio;
    }

    /**
     * 匹配用户ID规则
     */
    private boolean matchUserIdRule(ServerHttpRequest request, GrayRule.RuleCondition condition) {
        List<String> userIds = condition.getUserIds();
        if (userIds == null || userIds.isEmpty()) {
            return false;
        }
        String userId = getUserIdFromRequest(request);
        return userId != null && userIds.contains(userId);
    }

    /**
     * 匹配IP规则
     */
    private boolean matchIpRule(ServerHttpRequest request, GrayRule.RuleCondition condition) {
        List<String> ips = condition.getIps();
        if (ips == null || ips.isEmpty()) {
            return false;
        }
        String clientIp = getClientIp(request);
        return clientIp != null && ips.contains(clientIp);
    }

    /**
     * 匹配路径规则
     */
    private boolean matchPathRule(ServerHttpRequest request, GrayRule.RuleCondition condition) {
        String pathPattern = condition.getPathPattern();
        if (!StringUtils.hasText(pathPattern)) {
            return false;
        }
        String path = request.getURI().getPath();
        boolean pathMatch = pathMatcher.match(pathPattern, path);
        
        if (pathMatch && condition.getMethod() != null) {
            String method = request.getMethod() != null ? request.getMethod().name() : "";
            return condition.getMethod().equalsIgnoreCase(method);
        }
        return pathMatch;
    }

    /**
     * 获取一致性哈希键的值
     *
     * @param request     请求对象
     * @param keyConfig   键配置，如userId, ip, header:X-User-Id
     * @return 哈希键值
     */
    private String getConsistentHashKey(ServerHttpRequest request, String keyConfig) {
        if (!StringUtils.hasText(keyConfig)) {
            return null;
        }

        if ("userId".equalsIgnoreCase(keyConfig)) {
            return getUserIdFromRequest(request);
        } else if ("ip".equalsIgnoreCase(keyConfig)) {
            return getClientIp(request);
        } else if (keyConfig.startsWith("header:")) {
            String headerName = keyConfig.substring(7);
            return request.getHeaders().getFirst(headerName);
        }
        return null;
    }

    /**
     * 从请求中获取用户ID
     * 优先从Header X-User-Id获取，其次从Query参数获取
     */
    private String getUserIdFromRequest(ServerHttpRequest request) {
        String userId = request.getHeaders().getFirst("X-User-Id");
        if (userId == null) {
            userId = request.getQueryParams().getFirst("userId");
        }
        return userId;
    }

    /**
     * 获取客户端真实IP
     * 优先从X-Forwarded-For获取，其次从X-Real-IP获取
     */
    private String getClientIp(ServerHttpRequest request) {
        String ip = request.getHeaders().getFirst("X-Forwarded-For");
        if (ip != null && !ip.isEmpty() && !"unknown".equalsIgnoreCase(ip)) {
            int index = ip.indexOf(',');
            if (index != -1) {
                ip = ip.substring(0, index);
            }
            return ip.trim();
        }
        ip = request.getHeaders().getFirst("X-Real-IP");
        if (ip != null && !ip.isEmpty() && !"unknown".equalsIgnoreCase(ip)) {
            return ip.trim();
        }
        return request.getRemoteAddress() != null ? 
                request.getRemoteAddress().getAddress().getHostAddress() : null;
    }

    /**
     * 使用一致性哈希获取版本
     *
     * @param key   哈希键
     * @param ratio 灰度比例（可选）
     * @return 版本v1或v2
     */
    private String getVersionByConsistentHash(String key, Integer ratio) {
        if (consistentHashRing.isEmpty()) {
            return properties.getDefaultVersion();
        }
        long hash = hash(key);
        Map.Entry<Long, String> entry = consistentHashRing.ceilingEntry(hash);
        if (entry == null) {
            entry = consistentHashRing.firstEntry();
        }
        
        String version = entry.getValue();
        
        // 如果配置了比例，且命中了v2但比例不满足，则返回v1
        if (ratio != null && ratio < 100 && "v2".equals(version)) {
            int value = Math.abs(hash % 100);
            if (value >= ratio) {
                return "v1";
            }
        }
        return version;
    }

    /**
     * 根据版本获取URI
     *
     * @param version 版本v1或v2
     * @return 目标URI
     */
    private String getUriByVersion(String version) {
        return "v2".equals(version) ? properties.getV2Uri() : properties.getV1Uri();
    }

    /**
     * MD5哈希函数
     *
     * @param key 输入字符串
     * @return 哈希值
     */
    private long hash(String key) {
        try {
            MessageDigest md5 = MessageDigest.getInstance("MD5");
            byte[] digest = md5.digest(key.getBytes());
            long h = 0;
            for (int i = 0; i < 8; i++) {
                h <<= 8;
                h |= ((int) digest[i]) & 0xFF;
            }
            return h & Long.MAX_VALUE;
        } catch (NoSuchAlgorithmException e) {
            return (long) key.hashCode() & Long.MAX_VALUE;
        }
    }

    /**
     * 获取灰度统计信息
     *
     * @return 统计快照
     */
    public GrayStats.StatsSnapshot getGrayStats() {
        return grayStats.getSnapshot();
    }

    /**
     * 记录请求统计
     *
     * @param version 版本v1或v2
     * @param latency 延迟（毫秒）
     * @param success 是否成功
     */
    public void recordRequest(String version, long latency, boolean success) {
        if (!properties.isStatsEnabled()) {
            return;
        }
        if ("v2".equals(version)) {
            grayStats.recordV2Request(latency, success);
        } else {
            grayStats.recordV1Request(latency, success);
        }
    }

    /**
     * 新增/更新灰度规则
     * 支持热更新，无需重启
     *
     * @param rule 灰度规则
     * @return 更新后的规则
     */
    public GrayRule saveRule(GrayRule rule) {
        if (rule.getId() == null) {
            rule.setId(UUID.randomUUID().toString());
        }
        if (rule.getCreateTime() == null) {
            rule.setCreateTime(LocalDateTime.now());
        }
        rule.setUpdateTime(LocalDateTime.now());
        
        // 如果没有设置targetUri，根据版本自动设置
        if (rule.getTargetUri() == null) {
            rule.setTargetUri(getUriByVersion(rule.getTargetVersion()));
        }
        
        ruleMap.put(rule.getId(), rule);
        ruleVersion.incrementAndGet();
        log.info("灰度规则已保存: {}", rule);
        return rule;
    }

    /**
     * 删除灰度规则
     *
     * @param id 规则ID
     * @return 删除成功返回true
     */
    public boolean deleteRule(String id) {
        GrayRule removed = ruleMap.remove(id);
        if (removed != null) {
            ruleVersion.incrementAndGet();
            log.info("灰度规则已删除: id={}", id);
            return true;
        }
        return false;
    }

    /**
     * 获取所有灰度规则
     *
     * @return 规则列表
     */
    public List<GrayRule> getAllRules() {
        return new ArrayList<>(ruleMap.values());
    }

    /**
     * 根据ID获取规则
     *
     * @param id 规则ID
     * @return 灰度规则，不存在返回null
     */
    public GrayRule getRule(String id) {
        return ruleMap.get(id);
    }

    /**
     * 刷新规则，重新从配置文件加载
     */
    public void refreshRules() {
        ruleMap.clear();
        loadRulesFromProperties();
        log.info("灰度规则已刷新，当前规则数量: {}", ruleMap.size());
    }

    /**
     * 重置统计数据
     */
    public void resetStats() {
        grayStats.reset();
        log.info("灰度统计已重置");
    }

    /**
     * 路由版本信息
     */
    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class RouteVersion {
        /**
         * 版本号 v1/v2
         */
        private String version;
        /**
         * 目标URI
         */
        private String uri;
        /**
         * 是否匹配到灰度规则
         */
        private boolean matched;
        /**
         * 匹配的规则ID
         */
        private String matchedRuleId;
        /**
         * 匹配的规则名称
         */
        private String matchedRuleName;
    }
}
