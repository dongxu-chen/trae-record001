package com.risk.engine.rules;

import com.risk.engine.entity.EasyRule;
import com.risk.engine.repository.EasyRuleRepository;
import lombok.extern.slf4j.Slf4j;
import org.jeasy.rules.api.*;
import org.jeasy.rules.core.DefaultRulesEngine;
import org.jeasy.rules.core.RuleBuilder;
import org.jeasy.rules.mvel.MVELRule;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.ReadWriteLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

@Slf4j
@Component
public class DynamicRuleEngine {

    @Autowired
    private EasyRuleRepository ruleRepository;

    @Autowired
    private YamlRuleParser yamlRuleParser;

    private final ConcurrentHashMap<String, Rules> rulesByScene = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, List<EasyRule>> ruleEntitiesByScene = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, AtomicLong> ruleVersions = new ConcurrentHashMap<>();
    private final ReadWriteLock lock = new ReentrantReadWriteLock();

    @PostConstruct
    public void init() {
        try {
            log.info("初始化动态规则引擎...");
            loadAllRules();
            log.info("动态规则引擎初始化完成，场景数: {}", rulesByScene.size());
        } catch (Exception e) {
            log.error("动态规则引擎初始化失败", e);
        }
    }

    public void loadAllRules() {
        lock.writeLock().lock();
        try {
            List<String> scenes = ruleRepository.findAllEnabledScenes();
            for (String scene : scenes) {
                loadRulesForScene(scene);
            }
        } finally {
            lock.writeLock().unlock();
        }
    }

    private void loadRulesForScene(String scene) {
        List<EasyRule> enabledRules = ruleRepository.findBySceneAndStatus(scene, "ENABLED");
        ruleEntitiesByScene.put(scene, enabledRules);
        
        Rules rules = buildRules(enabledRules);
        rulesByScene.put(scene, rules);
        
        ruleVersions.computeIfAbsent(scene, k -> new AtomicLong(0)).incrementAndGet();
        log.info("场景 [{}] 规则加载完成，共 {} 条规则，版本: {}", 
            scene, enabledRules.size(), ruleVersions.get(scene).get());
    }

    private Rules buildRules(List<EasyRule> ruleEntities) {
        Rules rules = new Rules();
        
        for (EasyRule entity : ruleEntities) {
            try {
                Rule rule = buildRule(entity);
                rules.register(rule);
            } catch (Exception e) {
                log.error("构建规则失败: {}", entity.getRuleCode(), e);
            }
        }
        
        return rules;
    }

    private Rule buildRule(EasyRule entity) {
        if ("MVEL".equalsIgnoreCase(entity.getConditionType())) {
            return new MVELRule()
                .name(entity.getRuleCode())
                .description(entity.getDescription())
                .priority(entity.getPriority())
                .when(entity.getConditionExpr())
                .then(entity.getActionExpr());
        } else {
            return new RuleBuilder()
                .name(entity.getRuleCode())
                .description(entity.getDescription())
                .priority(entity.getPriority())
                .when(facts -> evaluateCondition(entity.getConditionExpr(), facts))
                .then(facts -> executeAction(entity.getActionExpr(), facts))
                .build();
        }
    }

    private boolean evaluateCondition(String expression, Facts facts) {
        try {
            Map<String, Object> context = new HashMap<>();
            for (String name : facts) {
                context.put(name, facts.get(name));
            }
            Object result = yamlRuleParser.evaluateExpression(expression, context);
            return result instanceof Boolean && (Boolean) result;
        } catch (Exception e) {
            log.error("条件评估失败: {}", expression, e);
            return false;
        }
    }

    private void executeAction(String expression, Facts facts) {
        try {
            Map<String, Object> context = new HashMap<>();
            for (String name : facts) {
                context.put(name, facts.get(name));
            }
            yamlRuleParser.evaluateExpression(expression, context);
            for (Map.Entry<String, Object> entry : context.entrySet()) {
                facts.put(entry.getKey(), entry.getValue());
            }
        } catch (Exception e) {
            log.error("动作执行失败: {}", expression, e);
        }
    }

    public void fireRules(String scene, Facts facts) {
        lock.readLock().lock();
        try {
            Rules rules = rulesByScene.get(scene);
            if (rules == null || rules.isEmpty()) {
                log.debug("场景 [{}] 无可用规则", scene);
                return;
            }
            
            RulesEngine engine = new DefaultRulesEngine();
            engine.fire(rules, facts);
        } finally {
            lock.readLock().unlock();
        }
    }

    public boolean reloadRules(String scene) {
        lock.writeLock().lock();
        try {
            log.info("热部署规则: 场景 [{}]", scene);
            loadRulesForScene(scene);
            return true;
        } catch (Exception e) {
            log.error("热部署规则失败: 场景 [{}]", scene, e);
            return false;
        } finally {
            lock.writeLock().unlock();
        }
    }

    public boolean reloadAllRules() {
        lock.writeLock().lock();
        try {
            log.info("热部署所有规则...");
            rulesByScene.clear();
            ruleEntitiesByScene.clear();
            loadAllRules();
            return true;
        } catch (Exception e) {
            log.error("热部署所有规则失败", e);
            return false;
        } finally {
            lock.writeLock().unlock();
        }
    }

    public void addRule(EasyRule rule) {
        lock.writeLock().lock();
        try {
            String scene = rule.getScene();
            List<EasyRule> rules = ruleEntitiesByScene.computeIfAbsent(scene, k -> new ArrayList<>());
            rules.removeIf(r -> r.getRuleCode().equals(rule.getRuleCode()));
            rules.add(rule);
            reloadRules(scene);
        } finally {
            lock.writeLock().unlock();
        }
    }

    public void removeRule(String scene, String ruleCode) {
        lock.writeLock().lock();
        try {
            List<EasyRule> rules = ruleEntitiesByScene.get(scene);
            if (rules != null) {
                rules.removeIf(r -> r.getRuleCode().equals(ruleCode));
                reloadRules(scene);
            }
        } finally {
            lock.writeLock().unlock();
        }
    }

    public long getRuleVersion(String scene) {
        AtomicLong version = ruleVersions.get(scene);
        return version != null ? version.get() : 0;
    }

    public Set<String> getRegisteredScenes() {
        return rulesByScene.keySet();
    }

    public int getRuleCount(String scene) {
        Rules rules = rulesByScene.get(scene);
        return rules != null ? rules.size() : 0;
    }

    public List<EasyRule> getRulesByScene(String scene) {
        return ruleEntitiesByScene.getOrDefault(scene, Collections.emptyList());
    }
}
