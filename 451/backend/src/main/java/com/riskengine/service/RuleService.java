package com.riskengine.service;

import com.riskengine.engine.core.RuleEngineExecutor;
import com.riskengine.engine.core.RuleHotReloadService;
import com.riskengine.engine.core.RuleVersionManager;
import com.riskengine.engine.drools.DroolsEngineManager;
import com.riskengine.engine.groovy.GroovyScriptEngine;
import com.riskengine.model.*;
import com.riskengine.redis.RedisRuleCacheService;
import com.riskengine.redis.RedisStatsService;
import com.riskengine.repository.RuleRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.Optional;

@Slf4j
@Service
public class RuleService {

    private final RuleRepository ruleRepository;
    private final RuleVersionManager versionManager;
    private final RuleHotReloadService hotReloadService;
    private final RuleEngineExecutor engineExecutor;
    private final RedisRuleCacheService ruleCacheService;
    private final RedisStatsService statsService;
    private final DroolsEngineManager droolsEngineManager;
    private final GroovyScriptEngine groovyScriptEngine;

    public RuleService(RuleRepository ruleRepository,
                       RuleVersionManager versionManager,
                       RuleHotReloadService hotReloadService,
                       RuleEngineExecutor engineExecutor,
                       RedisRuleCacheService ruleCacheService,
                       RedisStatsService statsService,
                       DroolsEngineManager droolsEngineManager,
                       GroovyScriptEngine groovyScriptEngine) {
        this.ruleRepository = ruleRepository;
        this.versionManager = versionManager;
        this.hotReloadService = hotReloadService;
        this.engineExecutor = engineExecutor;
        this.ruleCacheService = ruleCacheService;
        this.statsService = statsService;
        this.droolsEngineManager = droolsEngineManager;
        this.groovyScriptEngine = groovyScriptEngine;
    }

    public RuleDefinition createRule(RuleDefinition rule) {
        validateRule(rule);
        rule.setVersion(1);
        RuleDefinition saved = ruleRepository.save(rule);
        versionManager.createVersion(saved, "Initial version", "system");
        ruleCacheService.cacheRule(saved);
        return saved;
    }

    public RuleDefinition updateRule(Long id, RuleDefinition rule) {
        RuleDefinition existing = ruleRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Rule not found: " + id));

        existing.setRuleName(rule.getRuleName());
        existing.setRuleType(rule.getRuleType());
        existing.setRuleContent(rule.getRuleContent());
        existing.setDroolsDrl(rule.getDroolsDrl());
        existing.setGroovyScript(rule.getGroovyScript());
        existing.setPriority(rule.getPriority());
        existing.setEnabled(rule.getEnabled());
        existing.setDescription(rule.getDescription());
        existing.setSceneCode(rule.getSceneCode());
        existing.setVersion(existing.getVersion() + 1);

        validateRule(existing);

        RuleDefinition saved = ruleRepository.save(existing);
        versionManager.createVersion(saved, "Updated rule", "system");
        ruleCacheService.cacheRule(saved);

        if (saved.getEnabled()) {
            hotReloadService.hotReloadRule(saved);
        }

        return saved;
    }

    public Optional<RuleDefinition> getRule(Long id) {
        return ruleRepository.findById(id);
    }

    public Optional<RuleDefinition> getRuleByCode(String ruleCode) {
        return ruleRepository.findByRuleCode(ruleCode);
    }

    public List<RuleDefinition> getAllRules() {
        return ruleRepository.findAll();
    }

    public List<RuleDefinition> getEnabledRules() {
        return ruleRepository.findByEnabled(true);
    }

    public List<RuleDefinition> getRulesByScene(String sceneCode) {
        return ruleRepository.findBySceneCode(sceneCode);
    }

    public void deleteRule(Long id) {
        RuleDefinition rule = ruleRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Rule not found: " + id));
        hotReloadService.removeRule(rule.getRuleCode());
        ruleCacheService.removeRuleFromCache(rule.getRuleCode());
        ruleRepository.deleteById(id);
    }

    public List<RuleVersion> getVersionHistory(Long ruleId) {
        return versionManager.getVersionHistory(ruleId);
    }

    public RuleDefinition rollback(Long ruleId, Integer targetVersion) {
        RuleDefinition rule = ruleRepository.findById(ruleId)
                .orElseThrow(() -> new RuntimeException("Rule not found: " + ruleId));
        RuleDefinition rolledBack = versionManager.rollbackToVersion(rule, targetVersion);
        RuleDefinition saved = ruleRepository.save(rolledBack);
        versionManager.createVersion(saved, "Rollback to version " + targetVersion, "system");
        ruleCacheService.cacheRule(saved);

        if (saved.getEnabled()) {
            hotReloadService.hotReloadRule(saved);
        }

        return saved;
    }

    public void hotReloadAll() {
        List<RuleDefinition> enabledRules = getEnabledRules();
        hotReloadService.hotReloadAllRules(enabledRules);
    }

    public RiskDecision simulate(SimulateRequest request) {
        RuleDefinition rule = ruleRepository.findByRuleCode(request.getRuleCode())
                .orElseThrow(() -> new RuntimeException("Rule not found: " + request.getRuleCode()));

        List<RuleDefinition> rules = java.util.Collections.singletonList(rule);
        return engineExecutor.evaluate(request.getEvent(), rules);
    }

    public boolean validateDrl(String drl) {
        return droolsEngineManager.validateDrl(drl);
    }

    public boolean validateGroovy(String script) {
        return groovyScriptEngine.validateScript(script);
    }

    private void validateRule(RuleDefinition rule) {
        if (rule.getDroolsDrl() != null && !rule.getDroolsDrl().trim().isEmpty()) {
            if (!droolsEngineManager.validateDrl(rule.getDroolsDrl())) {
                throw new RuntimeException("Invalid Drools DRL for rule: " + rule.getRuleCode());
            }
        }
        if (rule.getGroovyScript() != null && !rule.getGroovyScript().trim().isEmpty()) {
            if (!groovyScriptEngine.validateScript(rule.getGroovyScript())) {
                throw new RuntimeException("Invalid Groovy script for rule: " + rule.getRuleCode());
            }
        }
    }

    public Map<String, Object> getGroovyClassLoaderStats() {
        return groovyScriptEngine.getClassLoaderStats();
    }

    public void triggerClassLoaderCleanup() {
        groovyScriptEngine.cleanupUnusedClassLoaders();
    }
}
