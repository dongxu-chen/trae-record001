package com.ratelimit.center.service;

import com.alibaba.csp.sentinel.datasource.Converter;
import com.alibaba.csp.sentinel.datasource.redis.config.RedisConnectionConfig;
import com.alibaba.csp.sentinel.datasource.redis.RedisDataSource;
import com.alibaba.csp.sentinel.slots.block.flow.FlowRule;
import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.TypeReference;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ratelimit.center.common.PageResult;
import com.ratelimit.center.common.RateLimitConstants;
import com.ratelimit.center.entity.FlowRuleEntity;
import com.ratelimit.center.mapper.FlowRuleMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import javax.annotation.PostConstruct;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Collectors;

@Slf4j
@Service
public class FlowRuleService {

    @Autowired
    private FlowRuleMapper flowRuleMapper;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @Value("${spring.data.redis.host:127.0.0.1}")
    private String redisHost;

    @Value("${spring.data.redis.port:6379}")
    private int redisPort;

    @Value("${spring.data.redis.password:}")
    private String redisPassword;

    private RedisDataSource<List<FlowRule>> redisDataSource;

    @PostConstruct
    public void init() {
        RedisConnectionConfig config = RedisConnectionConfig.builder()
                .withHost(redisHost)
                .withPort(redisPort)
                .withPassword(redisPassword.isEmpty() ? null : redisPassword)
                .build();

        Converter<String, List<FlowRule>> parser = source -> JSON.parseObject(source, new TypeReference<List<FlowRule>>() {});

        redisDataSource = new RedisDataSource<>(
                config,
                RateLimitConstants.REDIS_FLOW_RULES_KEY,
                RateLimitConstants.REDIS_FLOW_CHANNEL,
                parser
        );

        syncAllRulesToRedis();
    }

    public PageResult<FlowRuleEntity> list(String serviceName, String resource, Integer page, Integer size) {
        LambdaQueryWrapper<FlowRuleEntity> wrapper = new LambdaQueryWrapper<>();
        if (serviceName != null && !serviceName.isEmpty()) {
            wrapper.like(FlowRuleEntity::getServiceName, serviceName);
        }
        if (resource != null && !resource.isEmpty()) {
            wrapper.like(FlowRuleEntity::getResource, resource);
        }
        wrapper.orderByDesc(FlowRuleEntity::getCreateTime);

        Page<FlowRuleEntity> pageResult = flowRuleMapper.selectPage(new Page<>(page, size), wrapper);
        return PageResult.of(pageResult.getRecords(), pageResult.getTotal(), pageResult.getSize(), pageResult.getCurrent());
    }

    public FlowRuleEntity getById(Long id) {
        return flowRuleMapper.selectById(id);
    }

    public void save(FlowRuleEntity entity) {
        if (entity.getStatus() == null) {
            entity.setStatus(RateLimitConstants.STATUS_ENABLE);
        }
        flowRuleMapper.insert(entity);
        syncAllRulesToRedis();
    }

    public void update(FlowRuleEntity entity) {
        flowRuleMapper.updateById(entity);
        syncAllRulesToRedis();
    }

    public void delete(Long id) {
        flowRuleMapper.deleteById(id);
        syncAllRulesToRedis();
    }

    public void updateStatus(Long id, Integer status) {
        FlowRuleEntity entity = new FlowRuleEntity();
        entity.setId(id);
        entity.setStatus(status);
        flowRuleMapper.updateById(entity);
        syncAllRulesToRedis();
    }

    public void syncAllRulesToRedis() {
        CompletableFuture.runAsync(() -> {
            try {
                List<FlowRuleEntity> entities = flowRuleMapper.selectList(
                        new LambdaQueryWrapper<FlowRuleEntity>().eq(FlowRuleEntity::getStatus, RateLimitConstants.STATUS_ENABLE)
                );

                List<FlowRule> rules = new ArrayList<>();
                if (!CollectionUtils.isEmpty(entities)) {
                    rules = entities.stream()
                            .map(this::convertToFlowRule)
                            .collect(Collectors.toList());
                }

                String rulesJson = JSON.toJSONString(rules);
                stringRedisTemplate.opsForValue().set(RateLimitConstants.REDIS_FLOW_RULES_KEY, rulesJson);
                stringRedisTemplate.convertAndSend(RateLimitConstants.REDIS_FLOW_CHANNEL, rulesJson);

                log.info("Successfully synced {} flow rules to Redis", rules.size());
            } catch (Exception e) {
                log.error("Failed to sync flow rules to Redis", e);
            }
        });
    }

    private FlowRule convertToFlowRule(FlowRuleEntity entity) {
        FlowRule rule = new FlowRule();
        BeanUtils.copyProperties(entity, rule);
        rule.setLimitApp(entity.getLimitApp() != null ? entity.getLimitApp() : "default");

        if (entity.getClusterMode() != null && entity.getClusterMode()) {
            rule.setClusterMode(true);
            rule.setClusterConfig(new FlowRule.ClusterConfig()
                    .setClusterMode(true)
                    .setThresholdType(entity.getClusterThresholdType() != null ? entity.getClusterThresholdType() : 0)
                    .setFallbackToLocalWhenFail(entity.getClusterFallback() != null ? entity.getClusterFallback() : true)
            );
        }

        return rule;
    }
}
