package com.riskengine.engine.core;

import com.riskengine.engine.drools.DroolsEngineManager;
import com.riskengine.engine.groovy.GroovyScriptEngine;
import com.riskengine.model.*;
import lombok.extern.slf4j.Slf4j;
import org.kie.api.runtime.KieSession;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class RuleEngineExecutor {

    private final DroolsEngineManager droolsEngineManager;
    private final GroovyScriptEngine groovyScriptEngine;
    private final Map<String, RuleDefinition> activeRules = new ConcurrentHashMap<>();

    public RuleEngineExecutor(DroolsEngineManager droolsEngineManager,
                              GroovyScriptEngine groovyScriptEngine) {
        this.droolsEngineManager = droolsEngineManager;
        this.groovyScriptEngine = groovyScriptEngine;
    }

    public RiskDecision evaluate(RiskEvent event, List<RuleDefinition> rules) {
        RiskDecision decision = new RiskDecision();
        decision.setEventId(event.getEventId());
        decision.setHitRules(new ArrayList<>());
        decision.setRiskTags(new ArrayList<>());
        decision.setRiskScore(0);

        Map<String, Object> context = new HashMap<>();
        context.put("event", event);
        context.put("decision", decision);
        context.putAll(event.getPayload() != null ? event.getPayload() : new HashMap<>());

        List<RuleDefinition> droolsRules = new ArrayList<>();
        List<RuleDefinition> groovyRules = new ArrayList<>();

        for (RuleDefinition rule : rules) {
            if (!rule.getEnabled()) continue;
            if (rule.getDroolsDrl() != null && !rule.getDroolsDrl().trim().isEmpty()) {
                droolsRules.add(rule);
            }
            if (rule.getGroovyScript() != null && !rule.getGroovyScript().trim().isEmpty()) {
                groovyRules.add(rule);
            }
        }

        if (!droolsRules.isEmpty()) {
            evaluateDroolsRules(context, droolsRules, decision);
        }

        for (RuleDefinition rule : groovyRules) {
            evaluateGroovyRule(rule, context, decision);
        }

        if (decision.getRiskScore() == null) {
            decision.setRiskScore(0);
        }

        determineAction(decision);

        return decision;
    }

    private void evaluateDroolsRules(Map<String, Object> context, List<RuleDefinition> rules, RiskDecision decision) {
        try {
            droolsEngineManager.reloadRules(rules);
            KieSession kieSession = droolsEngineManager.getKieSession();
            if (kieSession == null) {
                log.warn("KieSession is null, skipping Drools evaluation");
                return;
            }

            try {
                kieSession.setGlobal("decision", decision);
                kieSession.insert(context.get("event"));

                for (Map.Entry<String, Object> entry : context.entrySet()) {
                    if (!"event".equals(entry.getKey()) && !"decision".equals(entry.getKey())) {
                        kieSession.insert(entry.getValue());
                    }
                }

                int firedRules = kieSession.fireAllRules();
                log.debug("Drools fired {} rules for event {}", firedRules, context.get("event"));
            } finally {
                kieSession.dispose();
            }
        } catch (Exception e) {
            log.error("Drools rule evaluation failed", e);
        }
    }

    private void evaluateGroovyRule(RuleDefinition rule, Map<String, Object> context, RiskDecision decision) {
        try {
            Object result = groovyScriptEngine.execute(rule, context);
            if (result != null) {
                if (result instanceof Boolean) {
                    if ((Boolean) result) {
                        decision.getHitRules().add(rule.getRuleCode());
                        decision.setRiskScore(decision.getRiskScore() + rule.getPriority());
                    }
                } else if (result instanceof Map) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> resultMap = (Map<String, Object>) result;
                    if (Boolean.TRUE.equals(resultMap.get("hit"))) {
                        decision.getHitRules().add(rule.getRuleCode());
                        if (resultMap.containsKey("riskScore")) {
                            decision.setRiskScore(decision.getRiskScore() + ((Number) resultMap.get("riskScore")).intValue());
                        }
                        if (resultMap.containsKey("riskTags")) {
                            @SuppressWarnings("unchecked")
                            List<String> tags = (List<String>) resultMap.get("riskTags");
                            decision.getRiskTags().addAll(tags);
                        }
                    }
                } else if (result instanceof Number) {
                    int score = ((Number) result).intValue();
                    if (score > 0) {
                        decision.getHitRules().add(rule.getRuleCode());
                        decision.setRiskScore(decision.getRiskScore() + score);
                    }
                }
            }
        } catch (Exception e) {
            log.error("Groovy rule evaluation failed for rule: {}", rule.getRuleCode(), e);
        }
    }

    private void determineAction(RiskDecision decision) {
        int score = decision.getRiskScore();
        if (score >= 300) {
            decision.setAction(RiskDecision.Action.BLOCK.name());
        } else if (score >= 200) {
            decision.setAction(RiskDecision.Action.REJECT.name());
        } else if (score >= 100) {
            decision.setAction(RiskDecision.Action.REVIEW.name());
        } else {
            decision.setAction(RiskDecision.Action.PASS.name());
        }
    }

    public void reloadActiveRules(List<RuleDefinition> rules) {
        activeRules.clear();
        for (RuleDefinition rule : rules) {
            if (rule.getEnabled()) {
                activeRules.put(rule.getRuleCode(), rule);
            }
        }
        log.info("Active rules reloaded, count: {}", activeRules.size());
    }

    public Map<String, RuleDefinition> getActiveRules() {
        return Collections.unmodifiableMap(activeRules);
    }
}
