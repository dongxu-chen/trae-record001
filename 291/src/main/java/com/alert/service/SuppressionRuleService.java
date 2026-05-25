package com.alert.service;

import com.alert.entity.AlertSuppressionRule;
import com.alert.repository.AlertSuppressionRuleRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
public class SuppressionRuleService {

    @Autowired
    private AlertSuppressionRuleRepository ruleRepository;

    public List<AlertSuppressionRule> getAllRules() {
        return ruleRepository.findAll();
    }

    public AlertSuppressionRule getRuleById(Long id) {
        return ruleRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("规则不存在: " + id));
    }

    @Transactional
    public AlertSuppressionRule createRule(AlertSuppressionRule rule) {
        if (rule.getPositionX() == null) rule.setPositionX(0);
        if (rule.getPositionY() == null) rule.setPositionY(0);
        return ruleRepository.save(rule);
    }

    @Transactional
    public AlertSuppressionRule updateRule(Long id, AlertSuppressionRule rule) {
        AlertSuppressionRule existing = getRuleById(id);
        existing.setRuleName(rule.getRuleName());
        existing.setParentCondition(rule.getParentCondition());
        existing.setChildCondition(rule.getChildCondition());
        existing.setEnabled(rule.getEnabled());
        existing.setDescription(rule.getDescription());
        if (rule.getPositionX() != null) existing.setPositionX(rule.getPositionX());
        if (rule.getPositionY() != null) existing.setPositionY(rule.getPositionY());
        return ruleRepository.save(existing);
    }

    @Transactional
    public AlertSuppressionRule updateRulePosition(Long id, Integer positionX, Integer positionY) {
        AlertSuppressionRule rule = getRuleById(id);
        rule.setPositionX(positionX);
        rule.setPositionY(positionY);
        return ruleRepository.save(rule);
    }

    @Transactional
    public void deleteRule(Long id) {
        ruleRepository.deleteById(id);
    }

    @Transactional
    public AlertSuppressionRule toggleRule(Long id) {
        AlertSuppressionRule rule = getRuleById(id);
        rule.setEnabled(!rule.getEnabled());
        return ruleRepository.save(rule);
    }
}
