package com.dlq.platform.analysis.analyzer;

import com.dlq.platform.analysis.rules.TimeoutRule;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.AlertLevelEnum;
import com.dlq.platform.common.enums.DeadReasonTypeEnum;
import org.jeasy.rules.api.Rules;
import org.jeasy.rules.api.RulesEngine;
import org.springframework.stereotype.Component;

@Component
public class TimeoutAnalyzer extends AbstractDeadLetterAnalyzer {

    private final Rules rules;

    public TimeoutAnalyzer(RulesEngine rulesEngine, TimeoutRule timeoutRule) {
        this.rulesEngine = rulesEngine;
        this.rules = new Rules(timeoutRule);
    }

    @Override
    public boolean support(DeadLetterMessage message) {
        String deadReason = message.getDeadReason();
        if (deadReason == null) {
            Integer retryCount = message.getRetryCount();
            return retryCount != null && retryCount > 3;
        }
        return deadReason.contains("timeout")
                || deadReason.contains("Timeout")
                || deadReason.contains("超时")
                || deadReason.contains("SocketTimeout")
                || deadReason.contains("ReadTimeout");
    }

    @Override
    protected Rules getRules() {
        return rules;
    }

    @Override
    protected DeadReasonTypeEnum getDeadReasonType() {
        return DeadReasonTypeEnum.TIMEOUT;
    }

    @Override
    protected AlertLevelEnum getDefaultRiskLevel() {
        return AlertLevelEnum.WARNING;
    }
}
