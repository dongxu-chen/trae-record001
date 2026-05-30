package com.riskengine.engine.core;

import com.riskengine.engine.drools.DroolsEngineManager;
import com.riskengine.engine.groovy.GroovyScriptEngine;
import com.riskengine.model.RuleDefinition;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;

@Slf4j
@Service
public class RuleHotReloadService {

    private final DroolsEngineManager droolsEngineManager;
    private final GroovyScriptEngine groovyScriptEngine;
    private final RuleEngineExecutor ruleEngineExecutor;
    private final RuleVersionManager ruleVersionManager;

    public RuleHotReloadService(DroolsEngineManager droolsEngineManager,
                                GroovyScriptEngine groovyScriptEngine,
                                RuleEngineExecutor ruleEngineExecutor,
                                RuleVersionManager ruleVersionManager) {
        this.droolsEngineManager = droolsEngineManager;
        this.groovyScriptEngine = groovyScriptEngine;
        this.ruleEngineExecutor = ruleEngineExecutor;
        this.ruleVersionManager = ruleVersionManager;
    }

    public synchronized void hotReloadRule(RuleDefinition rule) {
        log.info("Hot reloading rule: {}", rule.getRuleCode());

        if (rule.getGroovyScript() != null && !rule.getGroovyScript().trim().isEmpty()) {
            if (!groovyScriptEngine.validateScript(rule.getGroovyScript())) {
                throw new RuntimeException("Groovy script validation failed for rule: " + rule.getRuleCode());
            }
            groovyScriptEngine.reloadScript(rule.getRuleCode(), rule.getGroovyScript());
        }

        if (rule.getDroolsDrl() != null && !rule.getDroolsDrl().trim().isEmpty()) {
            if (!droolsEngineManager.validateDrl(rule.getDroolsDrl())) {
                throw new RuntimeException("Drools DRL validation failed for rule: " + rule.getRuleCode());
            }
        }

        log.info("Rule hot reload completed: {}", rule.getRuleCode());
    }

    public synchronized void hotReloadAllRules(List<RuleDefinition> rules) {
        log.info("Hot reloading all rules, count: {}", rules.size());

        try {
            droolsEngineManager.reloadRules(rules);
            for (RuleDefinition rule : rules) {
                if (rule.getEnabled() && rule.getGroovyScript() != null) {
                    groovyScriptEngine.reloadScript(rule.getRuleCode(), rule.getGroovyScript());
                }
            }
            ruleEngineExecutor.reloadActiveRules(rules);
            log.info("All rules hot reloaded successfully");
        } catch (Exception e) {
            log.error("Hot reload all rules failed", e);
            throw new RuntimeException("Hot reload failed: " + e.getMessage(), e);
        }
    }

    public synchronized void removeRule(String ruleCode) {
        groovyScriptEngine.removeScript(ruleCode);
        log.info("Rule removed from engine: {}", ruleCode);
    }
}
