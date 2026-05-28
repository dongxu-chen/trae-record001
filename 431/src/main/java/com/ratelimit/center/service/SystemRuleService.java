package com.ratelimit.center.service;

import com.alibaba.csp.sentinel.slots.system.SystemRule;
import com.alibaba.fastjson.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ratelimit.center.common.PageResult;
import com.ratelimit.center.common.RateLimitConstants;
import com.ratelimit.center.entity.SystemRuleEntity;
import com.ratelimit.center.mapper.SystemRuleMapper;
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
public class SystemRuleService {

    @Autowired
    private SystemRuleMapper systemRuleMapper;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @PostConstruct
    public void init() {
        syncAllRulesToRedis();
    }

    public PageResult<SystemRuleEntity> list(String serviceName, Integer page, Integer size) {
        LambdaQueryWrapper<SystemRuleEntity> wrapper = new LambdaQueryWrapper<>();
        if (serviceName != null && !serviceName.isEmpty()) {
            wrapper.like(SystemRuleEntity::getServiceName, serviceName);
        }
        wrapper.orderByDesc(SystemRuleEntity::getCreateTime);

        Page<SystemRuleEntity> pageResult = systemRuleMapper.selectPage(new Page<>(page, size), wrapper);
        return PageResult.of(pageResult.getRecords(), pageResult.getTotal(), pageResult.getSize(), pageResult.getCurrent());
    }

    public SystemRuleEntity getById(Long id) {
        return systemRuleMapper.selectById(id);
    }

    public void save(SystemRuleEntity entity) {
        if (entity.getStatus() == null) {
            entity.setStatus(RateLimitConstants.STATUS_ENABLE);
        }
        systemRuleMapper.insert(entity);
        syncAllRulesToRedis();
    }

    public void update(SystemRuleEntity entity) {
        systemRuleMapper.updateById(entity);
        syncAllRulesToRedis();
    }

    public void delete(Long id) {
        systemRuleMapper.deleteById(id);
        syncAllRulesToRedis();
    }

    public void updateStatus(Long id, Integer status) {
        SystemRuleEntity entity = new SystemRuleEntity();
        entity.setId(id);
        entity.setStatus(status);
        systemRuleMapper.updateById(entity);
        syncAllRulesToRedis();
    }

    public void syncAllRulesToRedis() {
        CompletableFuture.runAsync(() -> {
            try {
                List<SystemRuleEntity> entities = systemRuleMapper.selectList(
                        new LambdaQueryWrapper<SystemRuleEntity>().eq(SystemRuleEntity::getStatus, RateLimitConstants.STATUS_ENABLE)
                );

                List<SystemRule> rules = new ArrayList<>();
                if (!CollectionUtils.isEmpty(entities)) {
                    rules = entities.stream()
                            .map(this::convertToSystemRule)
                            .collect(Collectors.toList());
                }

                String rulesJson = JSON.toJSONString(rules);
                stringRedisTemplate.opsForValue().set(RateLimitConstants.REDIS_SYSTEM_RULES_KEY, rulesJson);
                stringRedisTemplate.convertAndSend(RateLimitConstants.REDIS_SYSTEM_CHANNEL, rulesJson);

                log.info("Successfully synced {} system rules to Redis", rules.size());
            } catch (Exception e) {
                log.error("Failed to sync system rules to Redis", e);
            }
        });
    }

    private SystemRule convertToSystemRule(SystemRuleEntity entity) {
        SystemRule rule = new SystemRule();
        BeanUtils.copyProperties(entity, rule);
        return rule;
    }
}
