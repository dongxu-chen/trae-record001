package com.riskengine.engine.conflict;

import com.riskengine.model.ConflictResult;
import com.riskengine.model.RuleDefinition;
import com.riskengine.repository.RuleRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Service
public class RuleConflictDetector {

    private final RuleRepository ruleRepository;

    public RuleConflictDetector(RuleRepository ruleRepository) {
        this.ruleRepository = ruleRepository;
    }

    public List<ConflictResult> detectConflicts() {
        List<RuleDefinition> rules = ruleRepository.findAll();
        List<ConflictResult> conflicts = new ArrayList<>();

        for (int i = 0; i < rules.size(); i++) {
            for (int j = i + 1; j < rules.size(); j++) {
                RuleDefinition a = rules.get(i);
                RuleDefinition b = rules.get(j);

                detectMutexConflicts(a, b, conflicts);
                detectRedundantConflicts(a, b, conflicts);
                detectOverlapConflicts(a, b, conflicts);
            }
        }

        conflicts.sort(Comparator.comparing(c -> {
            switch (c.getSeverity()) {
                case "HIGH": return 0;
                case "MEDIUM": return 1;
                default: return 2;
            }
        }));

        log.info("Conflict detection completed, found {} conflicts", conflicts.size());
        return conflicts;
    }

    private void detectMutexConflicts(RuleDefinition a, RuleDefinition b, List<ConflictResult> conflicts) {
        Set<String> fieldsA = extractConditionFields(a);
        Set<String> fieldsB = extractConditionFields(b);
        Set<String> commonFields = new HashSet<>(fieldsA);
        commonFields.retainAll(fieldsB);

        for (String field : commonFields) {
            Map<String, String> conditionsA = extractFieldConditions(a, field);
            Map<String, String> conditionsB = extractFieldConditions(b, field);

            if (isMutexCondition(conditionsA, conditionsB)) {
                ConflictResult cr = new ConflictResult();
                cr.setRuleCodeA(a.getRuleCode());
                cr.setRuleNameA(a.getRuleName());
                cr.setRuleCodeB(b.getRuleCode());
                cr.setRuleNameB(b.getRuleName());
                cr.setConflictType("MUTEX");
                cr.setSeverity("HIGH");
                cr.setDescription(String.format("规则互斥: 字段 %s 上条件冲突 — 规则A: %s, 规则B: %s",
                        field, conditionsA, conditionsB));
                cr.setSuggestion("检查两规则是否应同时启用，考虑禁用其中一条或修改条件");
                conflicts.add(cr);
            }
        }
    }

    private void detectRedundantConflicts(RuleDefinition a, RuleDefinition b, List<ConflictResult> conflicts) {
        if (!Objects.equals(a.getSceneCode(), b.getSceneCode())) return;
        if (a.getRuleType() == null || b.getRuleType() == null) return;

        boolean sameScene = Objects.equals(a.getSceneCode(), b.getSceneCode());
        boolean similarPriority = Math.abs(a.getPriority() - b.getPriority()) <= 10;
        Set<String> fieldsA = extractConditionFields(a);
        Set<String> fieldsB = extractConditionFields(b);

        if (sameScene && fieldsA.equals(fieldsB) && similarPriority) {
            Map<String, String> condA = extractAllConditions(a);
            Map<String, String> condB = extractAllConditions(b);
            if (condA.equals(condB)) {
                ConflictResult cr = new ConflictResult();
                cr.setRuleCodeA(a.getRuleCode());
                cr.setRuleNameA(a.getRuleName());
                cr.setRuleCodeB(b.getRuleCode());
                cr.setRuleNameB(b.getRuleName());
                cr.setConflictType("REDUNDANT");
                cr.setSeverity("MEDIUM");
                cr.setDescription(String.format("规则冗余: 两条规则在场景 %s 下条件完全相同，优先级相近(%d vs %d)",
                        a.getSceneCode(), a.getPriority(), b.getPriority()));
                cr.setSuggestion("合并或删除冗余规则，避免重复计算");
                conflicts.add(cr);
            }
        }
    }

    private void detectOverlapConflicts(RuleDefinition a, RuleDefinition b, List<ConflictResult> conflicts) {
        if (!Objects.equals(a.getSceneCode(), b.getSceneCode())) return;

        Set<String> fieldsA = extractConditionFields(a);
        Set<String> fieldsB = extractConditionFields(b);
        Set<String> common = new HashSet<>(fieldsA);
        common.retainAll(fieldsB);

        double overlapRatio = fieldsA.isEmpty() ? 0 : (double) common.size() / fieldsA.size();
        if (common.size() >= 2 && overlapRatio > 0.5 && !fieldsA.equals(fieldsB)) {
            boolean alreadyFound = conflicts.stream().anyMatch(c ->
                    (c.getRuleCodeA().equals(a.getRuleCode()) && c.getRuleCodeB().equals(b.getRuleCode()))
                    || (c.getRuleCodeA().equals(b.getRuleCode()) && c.getRuleCodeB().equals(a.getRuleCode())));
            if (!alreadyFound) {
                ConflictResult cr = new ConflictResult();
                cr.setRuleCodeA(a.getRuleCode());
                cr.setRuleNameA(a.getRuleName());
                cr.setRuleCodeB(b.getRuleCode());
                cr.setRuleNameB(b.getRuleName());
                cr.setConflictType("OVERLAP");
                cr.setSeverity("LOW");
                cr.setDescription(String.format("条件重叠: 规则在场景 %s 下有 %d 个共同字段 (%s)，重叠率 %.0f%%",
                        a.getSceneCode(), common.size(), common, overlapRatio * 100));
                cr.setSuggestion("检查是否需要调整条件范围，避免误判");
                conflicts.add(cr);
            }
        }
    }

    Set<String> extractConditionFields(RuleDefinition rule) {
        Set<String> fields = new HashSet<>();
        String content = rule.getGroovyScript();
        if (content != null) {
            Pattern p = Pattern.compile("event\\.(\\w+)");
            Matcher m = p.matcher(content);
            while (m.find()) {
                fields.add(m.group(1));
            }
        }
        content = rule.getDroolsDrl();
        if (content != null) {
            Pattern p = Pattern.compile("\\$(\\w+)\\s*:\\s*RiskEvent\\(([\\w.]+)\\s*[!=<>]+");
            Matcher m = p.matcher(content);
            while (m.find()) {
                String field = m.group(2);
                if (field.contains(".")) {
                    fields.add(field.substring(field.lastIndexOf('.') + 1));
                } else {
                    fields.add(field);
                }
            }
            Pattern p2 = Pattern.compile("event\\.(\\w+)");
            Matcher m2 = p2.matcher(content);
            while (m2.find()) {
                fields.add(m2.group(1));
            }
        }
        return fields;
    }

    Map<String, String> extractFieldConditions(RuleDefinition rule, String field) {
        Map<String, String> conditions = new HashMap<>();
        String content = rule.getGroovyScript();
        if (content != null) {
            Pattern p = Pattern.compile("event\\." + field + "\\s*([!=<>]+)\\s*\"?([^\"\\s)]+)\"?");
            Matcher m = p.matcher(content);
            while (m.find()) {
                conditions.put(field + "_" + m.group(1), m.group(2));
            }
        }
        content = rule.getDroolsDrl();
        if (content != null) {
            Pattern p = Pattern.compile(field + "\\s*([!=<>]+)\\s*\"?([^\"\\s)]+)\"?");
            Matcher m = p.matcher(content);
            while (m.find()) {
                conditions.put(field + "_" + m.group(1), m.group(2));
            }
        }
        return conditions;
    }

    Map<String, String> extractAllConditions(RuleDefinition rule) {
        Map<String, String> conditions = new HashMap<>();
        String content = rule.getGroovyScript();
        if (content != null) {
            Pattern p = Pattern.compile("event\\.(\\w+)\\s*([!=<>]+)\\s*\"?([^\"\\s)]+)\"?");
            Matcher m = p.matcher(content);
            while (m.find()) {
                conditions.put(m.group(1) + m.group(2), m.group(3));
            }
        }
        return conditions;
    }

    private boolean isMutexCondition(Map<String, String> condA, Map<String, String> condB) {
        for (Map.Entry<String, String> entryA : condA.entrySet()) {
            String opA = entryA.getKey();
            String valA = entryA.getValue();
            for (Map.Entry<String, String> entryB : condB.entrySet()) {
                String opB = entryB.getKey();
                String valB = entryB.getValue();
                if (isOppositeOperator(opA, opB) && valA.equals(valB)) {
                    return true;
                }
            }
        }
        return false;
    }

    private boolean isOppositeOperator(String opA, String opB) {
        Set<String[]> oppositePairs = Set.of(
                new String[]{"==", "!="},
                new String[]{">=", "<"},
                new String[]{"<=", ">"},
                new String[]{">", "<="},
                new String[]{"<", ">="}
        );
        return oppositePairs.stream().anyMatch(pair ->
                (pair[0].equals(opA) && pair[1].equals(opB))
                || (pair[1].equals(opA) && pair[0].equals(opB)));
    }
}
