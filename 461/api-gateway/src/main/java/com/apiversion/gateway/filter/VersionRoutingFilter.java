package com.apiversion.gateway.filter;

import com.apiversion.gateway.config.HeaderParseConfig;
import com.apiversion.gateway.strategy.HeaderParseStrategy;
import com.apiversion.gateway.strategy.HeaderParseStrategyFactory;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.http.HttpHeaders;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Component
@RequiredArgsConstructor
public class VersionRoutingFilter implements GlobalFilter, Ordered {

    private final ReactiveStringRedisTemplate redisTemplate;
    private final HeaderParseStrategyFactory strategyFactory;
    private final HeaderParseConfig headerParseConfig;
    private final ObjectMapper objectMapper;

    private static final String VERSION_HEADER = "X-API-Version";
    private static final String VERSION_PARAM = "version";
    private static final String DEFAULT_VERSION = "v1";
    private static final String VERSION_CONFIG_KEY = "api:version:config:";
    private static final String HEADER_RULES_KEY = "api:header:rules:";

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();
        HttpHeaders headers = request.getHeaders();

        String parsedVersion = parseVersionFromHeaders(headers, path);
        if (parsedVersion == null) {
            parsedVersion = request.getQueryParams().getFirst(VERSION_PARAM);
        }
        if (parsedVersion == null) {
            parsedVersion = DEFAULT_VERSION;
        }

        String finalRequestVersion = parsedVersion;
        return getHeaderRulesFromRedis(path)
                .defaultIfEmpty(new ArrayList<>())
                .flatMap(rules -> {
                    String version = finalRequestVersion;
                    if (CollectionUtils.isEmpty(rules)) {
                        rules = headerParseConfig.getRules();
                    }
                    if (!CollectionUtils.isEmpty(rules)) {
                        String parsed = parseVersionByRules(headers, rules);
                        if (parsed != null) {
                            version = parsed;
                        }
                    }
                    return Mono.just(version);
                })
                .flatMap(version -> redisTemplate.opsForValue().get(VERSION_CONFIG_KEY + path)
                        .defaultIfEmpty(DEFAULT_VERSION)
                        .flatMap(configVersion -> {
                            String targetVersion = version;
                            if (!version.equals(configVersion) && !DEFAULT_VERSION.equals(configVersion)) {
                                targetVersion = configVersion;
                            }

                            log.debug("请求路径: {}, 解析版本: {}, 配置版本: {}, 目标版本: {}",
                                    path, version, configVersion, targetVersion);

                            ServerHttpRequest modifiedRequest = request.mutate()
                                    .header(VERSION_HEADER, targetVersion)
                                    .build();

                            return chain.filter(exchange.mutate()
                                    .request(modifiedRequest)
                                    .build());
                        }));
    }

    private String parseVersionFromHeaders(HttpHeaders headers, String path) {
        String directValue = headers.getFirst(VERSION_HEADER);
        if (StringUtils.hasText(directValue)) {
            return directValue.trim();
        }

        List<String> acceptHeaders = headers.get("Accept");
        if (!CollectionUtils.isEmpty(acceptHeaders)) {
            for (String accept : acceptHeaders) {
                if (accept.contains("version=")) {
                    String version = extractVersionFromAccept(accept);
                    if (version != null) {
                        return version;
                    }
                }
            }
        }

        List<String> contentTypeHeaders = headers.get("Content-Type");
        if (!CollectionUtils.isEmpty(contentTypeHeaders)) {
            for (String contentType : contentTypeHeaders) {
                if (contentType.contains("version=")) {
                    String version = extractVersionFromAccept(contentType);
                    if (version != null) {
                        return version;
                    }
                }
            }
        }

        return null;
    }

    private String extractVersionFromAccept(String acceptHeader) {
        String[] parts = acceptHeader.split(";");
        for (String part : parts) {
            part = part.trim();
            if (part.startsWith("version=")) {
                return part.substring(8).trim();
            }
        }
        return null;
    }

    private Mono<List<HeaderParseConfig.HeaderParseRule>> getHeaderRulesFromRedis(String path) {
        return redisTemplate.opsForValue().get(HEADER_RULES_KEY + path)
                .map(json -> {
                    try {
                        return objectMapper.readValue(json,
                                new TypeReference<List<HeaderParseConfig.HeaderParseRule>>() {});
                    } catch (Exception e) {
                        log.warn("解析Header规则配置失败: {}", e.getMessage());
                        return new ArrayList<HeaderParseConfig.HeaderParseRule>();
                    }
                });
    }

    private String parseVersionByRules(HttpHeaders headers, List<HeaderParseConfig.HeaderParseRule> rules) {
        List<HeaderParseConfig.HeaderParseRule> sortedRules = rules.stream()
                .sorted(Comparator.comparing(
                        r -> r.getPriority() != null ? r.getPriority() : 100,
                        Comparator.nullsLast(Comparator.naturalOrder())))
                .collect(Collectors.toList());

        for (HeaderParseConfig.HeaderParseRule rule : sortedRules) {
            String headerValue = headers.getFirst(rule.getHeaderName());
            if (!StringUtils.hasText(headerValue)) {
                continue;
            }

            HeaderParseStrategy strategy = strategyFactory.getStrategy(rule.getParseStrategy());
            String parsed = strategy.parse(headerValue, rule.getPattern());

            if (StringUtils.hasText(parsed)) {
                log.debug("Header解析成功: header={}, strategy={}, value={}, result={}",
                        rule.getHeaderName(), rule.getParseStrategy(), headerValue, parsed);
                return parsed;
            }

            if (StringUtils.hasText(rule.getDefaultValue())) {
                log.debug("Header解析失败，使用默认值: header={}, default={}",
                        rule.getHeaderName(), rule.getDefaultValue());
                return rule.getDefaultValue();
            }
        }

        return null;
    }

    @Override
    public int getOrder() {
        return -100;
    }
}
