package com.apiversion.version.service.impl;

import cn.hutool.json.JSONUtil;
import com.apiversion.version.entity.HeaderParseRule;
import com.apiversion.version.entity.RoutingRule;
import com.apiversion.version.mapper.HeaderParseRuleMapper;
import com.apiversion.version.mapper.RoutingRuleMapper;
import com.apiversion.version.service.RoutingRuleService;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class RoutingRuleServiceImpl implements RoutingRuleService {

    private final RoutingRuleMapper routingRuleMapper;
    private final HeaderParseRuleMapper headerParseRuleMapper;
    private final StringRedisTemplate redisTemplate;

    private static final String HEADER_RULES_REDIS_KEY = "api:header:rules:";
    private static final String ROUTING_RULE_REDIS_KEY = "api:routing:rule:";

    @Override
    public IPage<RoutingRule> listRules(Page<RoutingRule> page, String apiName, Boolean enabled) {
        QueryWrapper<RoutingRule> wrapper = new QueryWrapper<>();
        if (StringUtils.hasText(apiName)) {
            wrapper.like("api_name", apiName);
        }
        if (enabled != null) {
            wrapper.eq("enabled", enabled);
        }
        wrapper.orderByDesc("create_time");
        return routingRuleMapper.selectPage(page, wrapper);
    }

    @Override
    public RoutingRule getRuleById(Long id) {
        RoutingRule rule = routingRuleMapper.selectById(id);
        if (rule != null) {
            List<HeaderParseRule> headerRules = headerParseRuleMapper.selectByRoutingRuleId(id);
            rule.setHeaderParseRules(convertToInnerHeaderRules(headerRules));
        }
        return rule;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public RoutingRule createRule(RoutingRule rule) {
        routingRuleMapper.insert(rule);

        if (!CollectionUtils.isEmpty(rule.getHeaderParseRules())) {
            for (RoutingRule.HeaderParseRule innerRule : rule.getHeaderParseRules()) {
                HeaderParseRule headerRule = convertToHeaderParseRule(innerRule);
                headerRule.setRoutingRuleId(rule.getId());
                headerParseRuleMapper.insert(headerRule);
            }
        }

        syncHeaderRulesToRedis(rule.getApiName());
        return getRuleById(rule.getId());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public RoutingRule updateRule(RoutingRule rule) {
        routingRuleMapper.updateById(rule);

        if (rule.getHeaderParseRules() != null) {
            QueryWrapper<HeaderParseRule> deleteWrapper = new QueryWrapper<>();
            deleteWrapper.eq("routing_rule_id", rule.getId());
            headerParseRuleMapper.delete(deleteWrapper);

            for (RoutingRule.HeaderParseRule innerRule : rule.getHeaderParseRules()) {
                HeaderParseRule headerRule = convertToHeaderParseRule(innerRule);
                headerRule.setRoutingRuleId(rule.getId());
                headerParseRuleMapper.insert(headerRule);
            }
        }

        syncHeaderRulesToRedis(rule.getApiName());
        return getRuleById(rule.getId());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteRule(Long id) {
        RoutingRule rule = routingRuleMapper.selectById(id);
        if (rule != null) {
            routingRuleMapper.deleteById(id);
            QueryWrapper<HeaderParseRule> deleteWrapper = new QueryWrapper<>();
            deleteWrapper.eq("routing_rule_id", id);
            headerParseRuleMapper.delete(deleteWrapper);

            redisTemplate.delete(HEADER_RULES_REDIS_KEY + rule.getApiName());
            redisTemplate.delete(ROUTING_RULE_REDIS_KEY + rule.getApiName());
        }
    }

    @Override
    public List<HeaderParseRule> getHeaderRulesByRoutingRuleId(Long routingRuleId) {
        return headerParseRuleMapper.selectByRoutingRuleId(routingRuleId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public HeaderParseRule createHeaderRule(HeaderParseRule rule) {
        headerParseRuleMapper.insert(rule);
        RoutingRule routingRule = routingRuleMapper.selectById(rule.getRoutingRuleId());
        if (routingRule != null) {
            syncHeaderRulesToRedis(routingRule.getApiName());
        }
        return rule;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public HeaderParseRule updateHeaderRule(HeaderParseRule rule) {
        headerParseRuleMapper.updateById(rule);
        RoutingRule routingRule = routingRuleMapper.selectById(rule.getRoutingRuleId());
        if (routingRule != null) {
            syncHeaderRulesToRedis(routingRule.getApiName());
        }
        return rule;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteHeaderRule(Long id) {
        HeaderParseRule rule = headerParseRuleMapper.selectById(id);
        if (rule != null) {
            headerParseRuleMapper.deleteById(id);
            RoutingRule routingRule = routingRuleMapper.selectById(rule.getRoutingRuleId());
            if (routingRule != null) {
                syncHeaderRulesToRedis(routingRule.getApiName());
            }
        }
    }

    @Override
    public void syncHeaderRulesToRedis(String apiPath) {
        QueryWrapper<RoutingRule> wrapper = new QueryWrapper<>();
        wrapper.eq("api_name", apiPath).eq("enabled", 1);
        List<RoutingRule> rules = routingRuleMapper.selectList(wrapper);

        if (!CollectionUtils.isEmpty(rules)) {
            for (RoutingRule rule : rules) {
                List<HeaderParseRule> headerRules = headerParseRuleMapper.selectByRoutingRuleId(rule.getId());
                if (!CollectionUtils.isEmpty(headerRules)) {
                    List<RoutingRule.HeaderParseRule> innerRules = convertToInnerHeaderRules(headerRules);
                    String json = JSONUtil.toJsonStr(innerRules);
                    redisTemplate.opsForValue().set(HEADER_RULES_REDIS_KEY + apiPath, json);
                    log.info("同步Header规则到Redis: path={}, rules={}", apiPath, json);
                }

                String ruleJson = JSONUtil.toJsonStr(rule);
                redisTemplate.opsForValue().set(ROUTING_RULE_REDIS_KEY + apiPath, ruleJson);
            }
        }
    }

    @Override
    public List<RoutingRule> getEnabledRules() {
        QueryWrapper<RoutingRule> wrapper = new QueryWrapper<>();
        wrapper.eq("enabled", 1);
        List<RoutingRule> rules = routingRuleMapper.selectList(wrapper);
        for (RoutingRule rule : rules) {
            List<HeaderParseRule> headerRules = headerParseRuleMapper.selectByRoutingRuleId(rule.getId());
            rule.setHeaderParseRules(convertToInnerHeaderRules(headerRules));
        }
        return rules;
    }

    private List<RoutingRule.HeaderParseRule> convertToInnerHeaderRules(List<HeaderParseRule> rules) {
        return rules.stream()
                .filter(HeaderParseRule::getEnabled)
                .map(this::convertToInnerHeaderRule)
                .collect(Collectors.toList());
    }

    private RoutingRule.HeaderParseRule convertToInnerHeaderRule(HeaderParseRule rule) {
        RoutingRule.HeaderParseRule innerRule = new RoutingRule.HeaderParseRule();
        innerRule.setHeaderName(rule.getHeaderName());
        innerRule.setParseStrategy(rule.getParseStrategy());
        innerRule.setPattern(rule.getPattern());
        innerRule.setDefaultValue(rule.getDefaultValue());
        innerRule.setPriority(rule.getPriority());
        return innerRule;
    }

    private HeaderParseRule convertToHeaderParseRule(RoutingRule.HeaderParseRule innerRule) {
        HeaderParseRule rule = new HeaderParseRule();
        rule.setHeaderName(innerRule.getHeaderName());
        rule.setParseStrategy(innerRule.getParseStrategy());
        rule.setPattern(innerRule.getPattern());
        rule.setDefaultValue(innerRule.getDefaultValue());
        rule.setPriority(innerRule.getPriority());
        rule.setEnabled(true);
        return rule;
    }
}
