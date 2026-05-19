package com.risk.engine.service;

import com.risk.engine.entity.Rule;
import com.risk.engine.repository.RuleRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Service
public class RuleService {

    @Autowired
    private RuleRepository ruleRepository;

    public Rule createRule(Rule rule) {
        if (ruleRepository.findByRuleCode(rule.getRuleCode()).isPresent()) {
            throw new RuntimeException("规则编码已存在: " + rule.getRuleCode());
        }
        return ruleRepository.save(rule);
    }

    public Optional<Rule> getRuleById(Long id) {
        return ruleRepository.findById(id);
    }

    public Optional<Rule> getRuleByCode(String ruleCode) {
        return ruleRepository.findByRuleCode(ruleCode);
    }

    public List<Rule> getAllRules() {
        return ruleRepository.findAll();
    }

    public List<Rule> getEnabledRules() {
        return ruleRepository.findByStatus("ENABLED");
    }

    public List<Rule> getEnabledRulesByScene(String scene) {
        return ruleRepository.findByStatusAndScene("ENABLED", scene);
    }

    @Transactional
    public Rule updateRule(Long id, Rule rule) {
        Rule existingRule = ruleRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("规则不存在: " + id));
        
        existingRule.setRuleName(rule.getRuleName());
        existingRule.setRuleDesc(rule.getRuleDesc());
        existingRule.setRuleContent(rule.getRuleContent());
        existingRule.setRuleType(rule.getRuleType());
        existingRule.setScene(rule.getScene());
        existingRule.setPriority(rule.getPriority());
        existingRule.setStatus(rule.getStatus());
        
        return ruleRepository.save(existingRule);
    }

    @Transactional
    public void deleteRule(Long id) {
        if (!ruleRepository.existsById(id)) {
            throw new RuntimeException("规则不存在: " + id);
        }
        ruleRepository.deleteById(id);
    }

    @Transactional
    public Rule updateRuleStatus(Long id, String status) {
        Rule rule = ruleRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("规则不存在: " + id));
        rule.setStatus(status);
        return ruleRepository.save(rule);
    }
}
