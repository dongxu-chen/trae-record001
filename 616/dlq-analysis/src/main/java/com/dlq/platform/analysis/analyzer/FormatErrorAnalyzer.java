package com.dlq.platform.analysis.analyzer;

import com.dlq.platform.analysis.rules.JsonFormatRule;
import com.dlq.platform.analysis.rules.RequiredFieldRule;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.AlertLevelEnum;
import com.dlq.platform.common.enums.DeadReasonTypeEnum;
import org.jeasy.rules.api.Rules;
import org.jeasy.rules.api.RulesEngine;
import org.springframework.stereotype.Component;

@Component
public class FormatErrorAnalyzer extends AbstractDeadLetterAnalyzer {

    private final Rules rules;

    public FormatErrorAnalyzer(RulesEngine rulesEngine,
                               JsonFormatRule jsonFormatRule,
                               RequiredFieldRule requiredFieldRule) {
        this.rulesEngine = rulesEngine;
        this.rules = new Rules(jsonFormatRule, requiredFieldRule);
    }

    @Override
    public boolean support(DeadLetterMessage message) {
        String deadReason = message.getDeadReason();
        if (deadReason == null) {
            return message.getMessageBody() != null;
        }
        return deadReason.contains("JsonParseException")
                || deadReason.contains("JSON")
                || deadReason.contains("格式")
                || deadReason.contains("类型不匹配")
                || deadReason.contains("InvalidFormatException");
    }

    @Override
    protected Rules getRules() {
        return rules;
    }

    @Override
    protected DeadReasonTypeEnum getDeadReasonType() {
        return DeadReasonTypeEnum.FORMAT_ERROR;
    }

    @Override
    protected AlertLevelEnum getDefaultRiskLevel() {
        return AlertLevelEnum.WARNING;
    }
}
