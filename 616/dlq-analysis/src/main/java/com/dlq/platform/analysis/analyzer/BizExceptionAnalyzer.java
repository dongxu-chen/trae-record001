package com.dlq.platform.analysis.analyzer;

import com.dlq.platform.analysis.rules.DatabaseAccessRule;
import com.dlq.platform.analysis.rules.NullPointerExceptionRule;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.AlertLevelEnum;
import com.dlq.platform.common.enums.DeadReasonTypeEnum;
import org.jeasy.rules.api.Rules;
import org.jeasy.rules.api.RulesEngine;
import org.springframework.stereotype.Component;

@Component
public class BizExceptionAnalyzer extends AbstractDeadLetterAnalyzer {

    private final Rules rules;

    public BizExceptionAnalyzer(RulesEngine rulesEngine,
                                NullPointerExceptionRule nullPointerExceptionRule,
                                DatabaseAccessRule databaseAccessRule) {
        this.rulesEngine = rulesEngine;
        this.rules = new Rules(nullPointerExceptionRule, databaseAccessRule);
    }

    @Override
    public boolean support(DeadLetterMessage message) {
        String stackTrace = message.getStackTrace();
        String deadReason = message.getDeadReason();

        if (stackTrace != null && !stackTrace.isEmpty()) {
            return true;
        }

        if (deadReason != null) {
            return deadReason.contains("Exception")
                    || deadReason.contains("异常")
                    || deadReason.contains("NullPointerException")
                    || deadReason.contains("SQLException")
                    || deadReason.contains("业务异常");
        }

        return false;
    }

    @Override
    protected Rules getRules() {
        return rules;
    }

    @Override
    protected DeadReasonTypeEnum getDeadReasonType() {
        return DeadReasonTypeEnum.BIZ_EXCEPTION;
    }

    @Override
    protected AlertLevelEnum getDefaultRiskLevel() {
        return AlertLevelEnum.CRITICAL;
    }
}
