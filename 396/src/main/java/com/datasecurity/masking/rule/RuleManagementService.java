package com.datasecurity.masking.rule;

import com.datasecurity.masking.enums.SensitiveType;
import com.datasecurity.masking.model.MaskPolicy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Service
public class RuleManagementService {

    @Autowired
    private RuleConfigLoader ruleConfigLoader;

    private final Map<String, CustomMaskRule> ruleCache = new ConcurrentHashMap<>();

    public List<CustomMaskRule> getAllRules() {
        return ruleConfigLoader.getAllRules();
    }

    public List<CustomMaskRule> getEnabledRules() {
        return ruleConfigLoader.getEnabledRules();
    }

    public CustomMaskRule getRuleById(String ruleId) {
        return ruleConfigLoader.getRuleById(ruleId);
    }

    public void addRule(CustomMaskRule rule) {
        ruleConfigLoader.addCustomRule(rule);
        ruleCache.put(rule.getId(), rule);
    }

    public boolean removeRule(String ruleId) {
        ruleCache.remove(ruleId);
        return ruleConfigLoader.removeRule(ruleId);
    }

    public CustomMaskRule matchByColumn(String columnName, String comment) {
        String lowerColumnName = columnName.toLowerCase();
        String lowerComment = comment != null ? comment.toLowerCase() : "";

        for (CustomMaskRule rule : ruleConfigLoader.getEnabledRules()) {
            if (matchKeywords(lowerColumnName, rule.getColumnKeywords()) ||
                    matchKeywords(lowerComment, rule.getCommentKeywords())) {
                log.debug("Matched rule '{}' for column '{}'", rule.getName(), columnName);
                return rule;
            }
        }
        return null;
    }

    public CustomMaskRule matchByValue(String value) {
        if (value == null || value.trim().isEmpty()) {
            return null;
        }

        String trimmedValue = value.trim();

        for (CustomMaskRule rule : ruleConfigLoader.getEnabledRules()) {
            Pattern pattern = rule.getValuePattern();
            if (pattern != null) {
                Matcher matcher = pattern.matcher(trimmedValue);
                if (matcher.matches()) {
                    log.debug("Matched rule '{}' by value pattern", rule.getName());
                    return rule;
                }
            }
        }
        return null;
    }

    public MaskPolicy toMaskPolicy(CustomMaskRule rule) {
        if (rule == null) {
            return null;
        }
        return MaskPolicy.builder()
                .strategy(rule.getDefaultStrategy())
                .maskChar(rule.getMaskChar())
                .keepStart(rule.getKeepStart())
                .keepEnd(rule.getKeepEnd())
                .replaceValue(rule.getReplaceValue())
                .hashAlgorithm(rule.getHashAlgorithm())
                .hashSalt(rule.getHashSalt())
                .build();
    }

    public SensitiveType toSensitiveType(CustomMaskRule rule) {
        if (rule == null) {
            return SensitiveType.UNKNOWN;
        }
        String ruleId = rule.getId();
        if (ruleId.startsWith("builtin_")) {
            String type = ruleId.replace("builtin_", "").toUpperCase();
            try {
                return SensitiveType.valueOf(type);
            } catch (IllegalArgumentException e) {
            }
        }
        return SensitiveType.UNKNOWN;
    }

    private boolean matchKeywords(String text, List<String> keywords) {
        if (text == null || text.isEmpty() || keywords == null || keywords.isEmpty()) {
            return false;
        }
        for (String keyword : keywords) {
            if (text.contains(keyword.toLowerCase())) {
                return true;
            }
        }
        return false;
    }
}
