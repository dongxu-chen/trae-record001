package com.ratelimit.center.config;

import com.alibaba.csp.sentinel.annotation.aspectj.SentinelResourceAspect;
import com.alibaba.csp.sentinel.datasource.ReadableDataSource;
import com.alibaba.csp.sentinel.datasource.redis.config.RedisConnectionConfig;
import com.alibaba.csp.sentinel.datasource.redis.RedisDataSource;
import com.alibaba.csp.sentinel.init.InitExecutor;
import com.alibaba.csp.sentinel.slots.block.RuleConstant;
import com.alibaba.csp.sentinel.slots.block.degrade.DegradeRule;
import com.alibaba.csp.sentinel.slots.block.degrade.DegradeRuleManager;
import com.alibaba.csp.sentinel.slots.block.flow.FlowRule;
import com.alibaba.csp.sentinel.slots.block.flow.FlowRuleManager;
import com.alibaba.csp.sentinel.slots.block.flow.param.ParamFlowRule;
import com.alibaba.csp.sentinel.slots.block.flow.param.ParamFlowRuleManager;
import com.alibaba.csp.sentinel.slots.system.SystemRule;
import com.alibaba.csp.sentinel.slots.system.SystemRuleManager;
import com.alibaba.csp.sentinel.transport.config.TransportConfig;
import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.TypeReference;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;

import javax.annotation.PostConstruct;
import java.util.List;

@Slf4j
@Configuration
public class SentinelConfig {

    @Value("${spring.data.redis.host:127.0.0.1}")
    private String redisHost;

    @Value("${spring.data.redis.port:6379}")
    private int redisPort;

    @Value("${spring.data.redis.password:}")
    private String redisPassword;

    @Value("${sentinel.transport.port:8719}")
    private int sentinelPort;

    @Value("${sentinel.transport.dashboard:127.0.0.1:8858}")
    private String sentinelDashboard;

    @PostConstruct
    @Order(-1)
    public void init() {
        System.setProperty(TransportConfig.SERVER_PORT, String.valueOf(sentinelPort));
        System.setProperty("csp.sentinel.dashboard.server", sentinelDashboard);
        System.setProperty("project.name", "rate-limit-center");
        System.setProperty("csp.sentinel.api.port", String.valueOf(sentinelPort));

        InitExecutor.doInit();
        log.info("Sentinel initialized, dashboard: {}, port: {}", sentinelDashboard, sentinelPort);
    }

    @Bean
    public SentinelResourceAspect sentinelResourceAspect() {
        return new SentinelResourceAspect();
    }

    @PostConstruct
    public void registerRuleDataSource() {
        RedisConnectionConfig redisConfig = RedisConnectionConfig.builder()
                .withHost(redisHost)
                .withPort(redisPort)
                .withPassword(redisPassword.isEmpty() ? null : redisPassword)
                .build();

        registerFlowRuleDataSource(redisConfig);
        registerDegradeRuleDataSource(redisConfig);
        registerParamFlowRuleDataSource(redisConfig);
        registerSystemRuleDataSource(redisConfig);
    }

    private void registerFlowRuleDataSource(RedisConnectionConfig config) {
        ReadableDataSource<String, List<FlowRule>> flowRuleDataSource = new RedisDataSource<>(
                config,
                "sentinel:flow:rules",
                "sentinel:flow:channel",
                source -> JSON.parseObject(source, new TypeReference<List<FlowRule>>() {})
        );
        FlowRuleManager.register2Property(flowRuleDataSource.getProperty());
        log.info("Flow rule data source registered with Redis");
    }

    private void registerDegradeRuleDataSource(RedisConnectionConfig config) {
        ReadableDataSource<String, List<DegradeRule>> degradeRuleDataSource = new RedisDataSource<>(
                config,
                "sentinel:degrade:rules",
                "sentinel:degrade:channel",
                source -> JSON.parseObject(source, new TypeReference<List<DegradeRule>>() {})
        );
        DegradeRuleManager.register2Property(degradeRuleDataSource.getProperty());
        log.info("Degrade rule data source registered with Redis");
    }

    private void registerParamFlowRuleDataSource(RedisConnectionConfig config) {
        ReadableDataSource<String, List<ParamFlowRule>> paramFlowRuleDataSource = new RedisDataSource<>(
                config,
                "sentinel:param:flow:rules",
                "sentinel:param:flow:channel",
                source -> JSON.parseObject(source, new TypeReference<List<ParamFlowRule>>() {})
        );
        ParamFlowRuleManager.register2Property(paramFlowRuleDataSource.getProperty());
        log.info("Param flow rule data source registered with Redis");
    }

    private void registerSystemRuleDataSource(RedisConnectionConfig config) {
        ReadableDataSource<String, List<SystemRule>> systemRuleDataSource = new RedisDataSource<>(
                config,
                "sentinel:system:rules",
                "sentinel:system:channel",
                source -> JSON.parseObject(source, new TypeReference<List<SystemRule>>() {})
        );
        SystemRuleManager.register2Property(systemRuleDataSource.getProperty());
        log.info("System rule data source registered with Redis");
    }
}
