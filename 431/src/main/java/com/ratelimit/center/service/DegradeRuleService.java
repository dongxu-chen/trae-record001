package com.ratelimit.center.service;

import com.alibaba.csp.sentinel.slots.block.degrade.DegradeRule;
import com.alibaba.fastjson.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ratelimit.center.common.PageResult;
import com.ratelimit.center.common.RateLimitConstants;
import com.ratelimit.center.entity.DegradeRuleEntity;
import com.ratelimit.center.mapper.DegradeRuleMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
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
public class DegradeRuleService {

    @Autowired
    private DegradeRuleMapper degradeRuleMapper;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @PostConstruct
    public void init() {
        syncAllRulesToRedis();
    }

    public PageResult<DegradeRuleEntity> list(String serviceName, String resource, Integer page, Integer size) {
        LambdaQueryWrapper<DegradeRuleEntity> wrapper = new LambdaQueryWrapper<>();
        if (serviceName != null && !serviceName.isEmpty()) {
            wrapper.like(DegradeRuleEntity::getServiceName, serviceName);
        }
        if (resource != null && !resource.isEmpty()) {
            wrapper.like(DegradeRuleEntity::getResource, resource);
        }
        wrapper.orderByDesc(DegradeRuleEntity::getCreateTime);

        Page<DegradeRuleEntity> pageResult = degradeRuleMapper.selectPage(new Page<>(page, size), wrapper);
        return PageResult.of(pageResult.getRecords(), pageResult.getTotal(), pageResult.getSize(), pageResult.getCurrent());
    }

    public DegradeRuleEntity getById(Long id) {
        return degradeRuleMapper.selectById(id);
    }

    public void save(DegradeRuleEntity entity) {
        if (entity.getStatus() == null) {
            entity.setStatus(RateLimitConstants.STATUS_ENABLE);
        }
        degradeRuleMapper.insert(entity);
        syncAllRulesToRedis();
    }

    public void update(DegradeRuleEntity entity) {
        degradeRuleMapper.updateById(entity);
        syncAllRulesToRedis();
    }

    public void delete(Long id) {
        degradeRuleMapper.deleteById(id);
        syncAllRulesToRedis();
    }

    public void updateStatus(Long id, Integer status) {
        DegradeRuleEntity entity = new DegradeRuleEntity();
        entity.setId(id);
        entity.setStatus(status);
        degradeRuleMapper.updateById(entity);
        syncAllRulesToRedis();
    }

    public void syncAllRulesToRedis() {
        CompletableFuture.runAsync(() -> {
            try {
                List<DegradeRuleEntity> entities = degradeRuleMapper.selectList(
                        new LambdaQueryWrapper<DegradeRuleEntity>().eq(DegradeRuleEntity::getStatus, RateLimitConstants.STATUS_ENABLE)
                );

                List<DegradeRule> rules = new ArrayList<>();
                if (!CollectionUtils.isEmpty(entities)) {
                    rules = entities.stream()
                            .map(this::convertToDegradeRule)
                            .collect(Collectors.toList());
                }

                String rulesJson = JSON.toJSONString(rules);
                stringRedisTemplate.opsForValue().set(RateLimitConstants.REDIS_DEGRADE_RULES_KEY, rulesJson);
                stringRedisTemplate.convertAndSend(RateLimitConstants.REDIS_DEGRADE_CHANNEL, rulesJson);

                log.info("Successfully synced {} degrade rules to Redis", rules.size());
            } catch (Exception e) {
                log.error("Failed to sync degrade rules to Redis", e);
            }
        });
    }

    private DegradeRule convertToDegradeRule(DegradeRuleEntity entity) {
        DegradeRule rule = new DegradeRule();
        BeanUtils.copyProperties(entity, rule);
        rule.setLimitApp(entity.getLimitApp() != null ? entity.getLimitApp() : "default");
        return rule;
    }
}
