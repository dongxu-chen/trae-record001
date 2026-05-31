package com.log.mask.rule;

import com.log.mask.core.MaskRule;
import com.log.mask.core.RegexMaskEngine;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class RuleEngine {
    private final Map<String, MaskRule> ruleMap = new ConcurrentHashMap<>();
    private final RegexMaskEngine maskEngine;

    public RuleEngine() {
        this.maskEngine = new RegexMaskEngine();
        loadDefaultRules();
    }

    public RuleEngine(RegexMaskEngine maskEngine) {
        this.maskEngine = maskEngine;
        loadDefaultRules();
    }

    private void loadDefaultRules() {
        List<MaskRule> defaultRules = maskEngine.getRules();
        for (MaskRule rule : defaultRules) {
            ruleMap.put(rule.getName(), rule);
        }
    }

    public void addRule(MaskRule rule) {
        ruleMap.put(rule.getName(), rule);
        syncToMaskEngine();
    }

    public void addRules(List<MaskRule> rules) {
        for (MaskRule rule : rules) {
            ruleMap.put(rule.getName(), rule);
        }
        syncToMaskEngine();
    }

    public boolean removeRule(String ruleName) {
        MaskRule removed = ruleMap.remove(ruleName);
        if (removed != null) {
            syncToMaskEngine();
            return true;
        }
        return false;
    }

    public void enableRule(String ruleName) {
        MaskRule rule = ruleMap.get(ruleName);
        if (rule != null) {
            rule.setEnabled(true);
            syncToMaskEngine();
        }
    }

    public void disableRule(String ruleName) {
        MaskRule rule = ruleMap.get(ruleName);
        if (rule != null) {
            rule.setEnabled(false);
            syncToMaskEngine();
        }
    }

    public MaskRule getRule(String ruleName) {
        return ruleMap.get(ruleName);
    }

    public List<MaskRule> getAllRules() {
        List<MaskRule> allRules = new ArrayList<>(ruleMap.values());
        allRules.sort((a, b) -> Integer.compare(b.getPriority(), a.getPriority()));
        return allRules;
    }

    public List<MaskRule> getEnabledRules() {
        List<MaskRule> enabled = new ArrayList<>();
        for (MaskRule rule : ruleMap.values()) {
            if (rule.isEnabled()) {
                enabled.add(rule);
            }
        }
        enabled.sort((a, b) -> Integer.compare(b.getPriority(), a.getPriority()));
        return enabled;
    }

    private void syncToMaskEngine() {
        maskEngine.clearRules();
        for (MaskRule rule : ruleMap.values()) {
            if (rule.isEnabled()) {
                maskEngine.addRule(rule);
            }
        }
    }

    public String applyRules(String content) {
        return maskEngine.mask(content);
    }

    public RegexMaskEngine getMaskEngine() {
        return maskEngine;
    }

    public void clearAllRules() {
        ruleMap.clear();
        maskEngine.clearRules();
    }

    public void resetToDefault() {
        ruleMap.clear();
        maskEngine.clearRules();
        loadDefaultRules();
    }
}
