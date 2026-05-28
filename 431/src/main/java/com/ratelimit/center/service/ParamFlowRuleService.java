package com.ratelimit.center.service;

import com.alibaba.csp.sentinel.slots.block.flow.param.ParamFlowRule;
import com.alibaba.fastjson.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ratelimit.center.common.PageResult;
import com.ratelimit.center.common.RateLimitConstants;
import com.ratelimit.center.entity.ParamFlowRuleEntity;
import com.ratelimit.center.mapper.ParamFlowRuleMapper;
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
public class ParamFlowRuleService {

    @Autowired
    private ParamFlowRuleMapper paramFlowRuleMapper;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @PostConstruct
    public void init() {
        syncAllRulesToRedis();
    }

    public PageResult<ParamFlowRuleEntity> list(String serviceName, String resource, Integer page, Integer size) {
        LambdaQueryWrapper<ParamFlowRuleEntity> wrapper = new LambdaQueryWrapper<>();
        if (serviceName != null && !serviceName.isEmpty()) {
            wrapper.like(ParamFlowRuleEntity::getServiceName, serviceName);
        }
        if (resource != null && !resource.isEmpty()) {
            wrapper.like(ParamFlowRuleEntity::getResource, resource);
        }
        wrapper.orderByDesc(ParamFlowRuleEntity::getCreateTime);

        Page<ParamFlowRuleEntity> pageResult = paramFlowRuleMapper.selectPage(new Page<>(page, size), wrapper);
        return PageResult.of(pageResult.getRecords(), pageResult.getTotal(), pageResult.getSize(), pageResult.getCurrent());
    }

    public ParamFlowRuleEntity getById(Long id) {
        return paramFlowRuleMapper.selectById(id);
    }

    public void save(ParamFlowRuleEntity entity) {
        if (entity.getStatus() == null) {
            entity.setStatus(RateLimitConstants.STATUS_ENABLE);
        }
        paramFlowRuleMapper.insert(entity);
        syncAllRulesToRedis();
    }

    public void update(ParamFlowRuleEntity entity) {
        paramFlowRuleMapper.updateById(entity);
        syncAllRulesToRedis();
    }

    public void delete(Long id) {
        paramFlowRuleMapper.deleteById(id);
        syncAllRulesToRedis();
    }

    public void updateStatus(Long id, Integer status) {
        ParamFlowRuleEntity entity = new ParamFlowRuleEntity();
        entity.setId(id);
        entity.setStatus(status);
        paramFlowRuleMapper.updateById(entity);
        syncAllRulesToRedis();
    }

    public void syncAllRulesToRedis() {
        CompletableFuture.runAsync(() -> {
            try {
                List<ParamFlowRuleEntity> entities = paramFlowRuleMapper.selectList(
                        new LambdaQueryWrapper<ParamFlowRuleEntity>().eq(ParamFlowRuleEntity::getStatus, RateLimitConstants.STATUS_ENABLE)
                );

                List<ParamFlowRule> rules = new ArrayList<>();
                if (!CollectionUtils.isEmpty(entities)) {
                    rules = entities.stream()
                            .map(this::convertToParamFlowRule)
                            .collect(Collectors.toList());
                }

                String rulesJson = JSON.toJSONString(rules);
                stringRedisTemplate.opsForValue().set(RateLimitConstants.REDIS_PARAM_FLOW_RULES_KEY, rulesJson);
                stringRedisTemplate.convertAndSend(RateLimitConstants.REDIS_PARAM_FLOW_CHANNEL, rulesJson);

                log.info("Successfully synced {} param flow rules to Redis", rules.size());
            } catch (Exception e) {
                log.error("Failed to sync param flow rules to Redis", e);
            }
        });
    }

    private ParamFlowRule convertToParamFlowRule(ParamFlowRuleEntity entity) {
        ParamFlowRule rule = new ParamFlowRule();
        BeanUtils.copyProperties(entity, rule);
        return rule;
    }
}
