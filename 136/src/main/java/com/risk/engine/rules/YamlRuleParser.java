package com.risk.engine.rules;

import com.risk.engine.entity.EasyRule;
import org.mvel2.MVEL;
import org.springframework.stereotype.Component;
import org.yaml.snakeyaml.Yaml;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.util.*;

@Component
public class YamlRuleParser {

    public List<RuleDefinition> parseYaml(String yamlContent) {
        Yaml yaml = new Yaml();
        try (InputStream is = new ByteArrayInputStream(yamlContent.getBytes())) {
            Map<String, Object> root = yaml.load(is);
            List<Map<String, Object>> rulesList = (List<Map<String, Object>>) root.get("rules");
            List<RuleDefinition> definitions = new ArrayList<>();
            
            if (rulesList != null) {
                for (Map<String, Object> ruleMap : rulesList) {
                    RuleDefinition definition = new RuleDefinition();
                    definition.setRuleCode((String) ruleMap.get("ruleCode"));
                    definition.setRuleName((String) ruleMap.get("name"));
                    definition.setDescription((String) ruleMap.get("description"));
                    definition.setScene((String) ruleMap.getOrDefault("scene", "DEFAULT"));
                    definition.setPriority((Integer) ruleMap.getOrDefault("priority", 0));
                    definition.setVersion((String) ruleMap.get("version"));
                    definition.setTags((String) ruleMap.get("tags"));
                    
                    Map<String, Object> conditionMap = (Map<String, Object>) ruleMap.get("condition");
                    if (conditionMap != null) {
                        RuleDefinition.Condition condition = new RuleDefinition.Condition();
                        condition.setType((String) conditionMap.getOrDefault("type", "MVEL"));
                        condition.setExpression((String) conditionMap.get("expression"));
                        condition.setParams((Map<String, Object>) conditionMap.get("params"));
                        definition.setCondition(condition);
                    }
                    
                    Map<String, Object> actionMap = (Map<String, Object>) ruleMap.get("action");
                    if (actionMap != null) {
                        RuleDefinition.Action action = new RuleDefinition.Action();
                        action.setType((String) actionMap.getOrDefault("type", "MVEL"));
                        action.setExpression((String) actionMap.get("expression"));
                        action.setParams((Map<String, Object>) actionMap.get("params"));
                        definition.setAction(action);
                    }
                    
                    definitions.add(definition);
                }
            }
            return definitions;
        } catch (Exception e) {
            throw new RuntimeException("YAML规则解析失败: " + e.getMessage(), e);
        }
    }

    public String toYaml(List<RuleDefinition> rules) {
        Map<String, Object> root = new HashMap<>();
        List<Map<String, Object>> rulesList = new ArrayList<>();
        
        for (RuleDefinition rule : rules) {
            Map<String, Object> ruleMap = new LinkedHashMap<>();
            ruleMap.put("ruleCode", rule.getRuleCode());
            ruleMap.put("name", rule.getRuleName());
            ruleMap.put("description", rule.getDescription());
            ruleMap.put("scene", rule.getScene());
            ruleMap.put("priority", rule.getPriority());
            
            if (rule.getCondition() != null) {
                Map<String, Object> conditionMap = new LinkedHashMap<>();
                conditionMap.put("type", rule.getCondition().getType());
                conditionMap.put("expression", rule.getCondition().getExpression());
                conditionMap.put("params", rule.getCondition().getParams());
                ruleMap.put("condition", conditionMap);
            }
            
            if (rule.getAction() != null) {
                Map<String, Object> actionMap = new LinkedHashMap<>();
                actionMap.put("type", rule.getAction().getType());
                actionMap.put("expression", rule.getAction().getExpression());
                actionMap.put("params", rule.getAction().getParams());
                ruleMap.put("action", actionMap);
            }
            
            ruleMap.put("version", rule.getVersion());
            ruleMap.put("tags", rule.getTags());
            rulesList.add(ruleMap);
        }
        
        root.put("rules", rulesList);
        Yaml yaml = new Yaml();
        return yaml.dump(root);
    }

    public EasyRule toEntity(RuleDefinition definition) {
        EasyRule entity = new EasyRule();
        entity.setRuleCode(definition.getRuleCode());
        entity.setRuleName(definition.getRuleName());
        entity.setDescription(definition.getDescription());
        entity.setScene(definition.getScene());
        entity.setPriority(definition.getPriority());
        entity.setVersion(definition.getVersion());
        entity.setTags(definition.getTags());
        
        if (definition.getCondition() != null) {
            entity.setConditionType(definition.getCondition().getType());
            entity.setConditionExpr(definition.getCondition().getExpression());
        }
        
        if (definition.getAction() != null) {
            entity.setActionType(definition.getAction().getType());
            entity.setActionExpr(definition.getAction().getExpression());
        }
        
        return entity;
    }

    public RuleDefinition fromEntity(EasyRule entity) {
        RuleDefinition definition = new RuleDefinition();
        definition.setRuleCode(entity.getRuleCode());
        definition.setRuleName(entity.getRuleName());
        definition.setDescription(entity.getDescription());
        definition.setScene(entity.getScene());
        definition.setPriority(entity.getPriority());
        definition.setVersion(entity.getVersion());
        definition.setTags(entity.getTags());
        
        RuleDefinition.Condition condition = new RuleDefinition.Condition();
        condition.setType(entity.getConditionType());
        condition.setExpression(entity.getConditionExpr());
        definition.setCondition(condition);
        
        RuleDefinition.Action action = new RuleDefinition.Action();
        action.setType(entity.getActionType());
        action.setExpression(entity.getActionExpr());
        definition.setAction(action);
        
        return definition;
    }

    public boolean validateExpression(String expression) {
        try {
            MVEL.compileExpression(expression);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    public Object evaluateExpression(String expression, Map<String, Object> context) {
        try {
            return MVEL.eval(expression, context);
        } catch (Exception e) {
            throw new RuntimeException("表达式执行失败: " + e.getMessage(), e);
        }
    }
}
