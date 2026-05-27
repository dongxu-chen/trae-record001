package com.datasecurity.masking.recognizer;

import com.datasecurity.masking.enums.SensitiveType;
import com.datasecurity.masking.rule.CustomMaskRule;
import com.datasecurity.masking.rule.RuleManagementService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class SensitiveFieldRecognizer {

    @Autowired
    private RuleManagementService ruleManagementService;

    public SensitiveType recognizeByColumnName(String columnName, String comment) {
        CustomMaskRule rule = ruleManagementService.matchByColumn(columnName, comment);
        if (rule != null) {
            return ruleManagementService.toSensitiveType(rule);
        }
        return SensitiveType.UNKNOWN;
    }

    public CustomMaskRule recognizeRuleByColumnName(String columnName, String comment) {
        return ruleManagementService.matchByColumn(columnName, comment);
    }

    public SensitiveType recognizeByValue(String value) {
        CustomMaskRule rule = recognizeRuleByValue(value);
        if (rule != null) {
            return ruleManagementService.toSensitiveType(rule);
        }
        return SensitiveType.UNKNOWN;
    }

    public CustomMaskRule recognizeRuleByValue(String value) {
        return ruleManagementService.matchByValue(value);
    }

    public CustomMaskRule getMatchedRule(String columnName, String comment, String sampleValue) {
        CustomMaskRule columnMatch = recognizeRuleByColumnName(columnName, comment);
        if (columnMatch != null) {
            return columnMatch;
        }
        if (sampleValue != null && !sampleValue.isEmpty()) {
            return recognizeRuleByValue(sampleValue);
        }
        return null;
    }
}
            return SensitiveType.NAME;
        }
        if (matchKeywords(lowerColumnName, comment, EMAIL_KEYWORDS)) {
            return SensitiveType.EMAIL;
        }
        if (matchKeywords(lowerColumnName, comment, ADDRESS_KEYWORDS)) {
            return SensitiveType.ADDRESS;
        }

        return SensitiveType.UNKNOWN;
    }

    public SensitiveType recognizeByValue(String value) {
        if (value == null || value.trim().isEmpty()) {
            return SensitiveType.UNKNOWN;
        }

        String trimmedValue = value.trim();

        if (matchesPattern(trimmedValue, SensitiveType.ID_CARD.getRegex())) {
            return SensitiveType.ID_CARD;
        }
        if (matchesPattern(trimmedValue, SensitiveType.PHONE.getRegex())) {
            return SensitiveType.PHONE;
        }
        if (matchesPattern(trimmedValue, SensitiveType.BANK_CARD.getRegex())) {
            return SensitiveType.BANK_CARD;
        }
        if (matchesPattern(trimmedValue, SensitiveType.EMAIL.getRegex())) {
            return SensitiveType.EMAIL;
        }

        return SensitiveType.UNKNOWN;
    }

    private boolean matchKeywords(String columnName, String comment, List<String> keywords) {
        for (String keyword : keywords) {
            if (columnName.contains(keyword.toLowerCase())) {
                return true;
            }
        }
        if (comment != null && !comment.isEmpty()) {
            String lowerComment = comment.toLowerCase();
            for (String keyword : keywords) {
                if (lowerComment.contains(keyword.toLowerCase())) {
                    return true;
                }
            }
        }
        return false;
    }

    private boolean matchesPattern(String value, String regex) {
        if (regex == null) {
            return false;
        }
        return Pattern.matches(regex, value);
    }
}
