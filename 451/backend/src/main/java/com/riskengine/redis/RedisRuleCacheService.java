package com.riskengine.redis;

import com.alibaba.fastjson.JSON;
import com.riskengine.model.RuleDefinition;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class RedisRuleCacheService {

    private static final String RULE_CACHE_PREFIX = "risk:rule:";
    private static final String RULE_LIST_KEY = "risk:rule:list";
    private static final long CACHE_TTL_HOURS = 24;

    private final StringRedisTemplate redisTemplate;

    public RedisRuleCacheService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public void cacheRule(RuleDefinition rule) {
        try {
            String key = RULE_CACHE_PREFIX + rule.getRuleCode();
            redisTemplate.opsForValue().set(key, JSON.toJSONString(rule), CACHE_TTL_HOURS, TimeUnit.HOURS);
            redisTemplate.opsForSet().add(RULE_LIST_KEY, rule.getRuleCode());
        } catch (Exception e) {
            log.error("Failed to cache rule: {}", rule.getRuleCode(), e);
        }
    }

    public void removeRuleFromCache(String ruleCode) {
        try {
            redisTemplate.delete(RULE_CACHE_PREFIX + ruleCode);
            redisTemplate.opsForSet().remove(RULE_LIST_KEY, ruleCode);
        } catch (Exception e) {
            log.error("Failed to remove rule from cache: {}", ruleCode, e);
        }
    }

    public RuleDefinition getCachedRule(String ruleCode) {
        try {
            String json = redisTemplate.opsForValue().get(RULE_CACHE_PREFIX + ruleCode);
            if (json != null) {
                return JSON.parseObject(json, RuleDefinition.class);
            }
        } catch (Exception e) {
            log.error("Failed to get cached rule: {}", ruleCode, e);
        }
        return null;
    }

    public List<RuleDefinition> getAllCachedRules() {
        List<RuleDefinition> rules = new ArrayList<>();
        try {
            Set<String> ruleCodes = redisTemplate.opsForSet().members(RULE_LIST_KEY);
            if (ruleCodes != null) {
                for (String ruleCode : ruleCodes) {
                    RuleDefinition rule = getCachedRule(ruleCode);
                    if (rule != null) {
                        rules.add(rule);
                    }
                }
            }
        } catch (Exception e) {
            log.error("Failed to get all cached rules", e);
        }
        return rules;
    }

    public void refreshAllRules(List<RuleDefinition> rules) {
        try {
            Set<String> existingCodes = redisTemplate.opsForSet().members(RULE_LIST_KEY);
            if (existingCodes != null) {
                for (String code : existingCodes) {
                    redisTemplate.delete(RULE_CACHE_PREFIX + code);
                }
            }
            redisTemplate.delete(RULE_LIST_KEY);

            for (RuleDefinition rule : rules) {
                cacheRule(rule);
            }
            log.info("All rules refreshed in Redis cache, count: {}", rules.size());
        } catch (Exception e) {
            log.error("Failed to refresh all rules in cache", e);
        }
    }
}
