package com.dlq.platform.analysis.analyzer;

import com.dlq.platform.analysis.model.AnalysisResult;
import com.dlq.platform.common.dto.DeadLetterAnalysisResult;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.AlertLevelEnum;
import com.dlq.platform.common.enums.DeadReasonTypeEnum;
import lombok.extern.slf4j.Slf4j;
import org.jeasy.rules.api.Facts;
import org.jeasy.rules.api.Rules;
import org.jeasy.rules.api.RulesEngine;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Slf4j
public abstract class AbstractDeadLetterAnalyzer implements DeadLetterAnalyzer {

    @Autowired
    protected RulesEngine rulesEngine;

    protected abstract Rules getRules();

    protected abstract DeadReasonTypeEnum getDeadReasonType();

    protected abstract AlertLevelEnum getDefaultRiskLevel();

    @Override
    public AnalysisResult analyze(DeadLetterMessage message) {
        try {
            Facts facts = new Facts();
            facts.put("message", message);
            facts.put("result", AnalysisResult.builder()
                    .reasonType(getDeadReasonType())
                    .confidence(0.0)
                    .details(new HashMap<>())
                    .build());

            rulesEngine.fire(getRules(), facts);

            AnalysisResult result = facts.get("result");
            if (result.getConfidence() > 0) {
                postProcess(result, message);
            }
            return result;
        } catch (Exception e) {
            log.error("分析死信消息失败, messageId: {}", message.getMessageId(), e);
            return AnalysisResult.builder()
                    .reasonType(DeadReasonTypeEnum.OTHER)
                    .confidence(0.1)
                    .rootCause("分析过程发生异常: " + e.getMessage())
                    .suggestedAction("请检查分析器配置和日志")
                    .build();
        }
    }

    @Override
    public DeadLetterAnalysisResult analyzeToDto(DeadLetterMessage message) {
        AnalysisResult analysisResult = analyze(message);
        return DeadLetterAnalysisResult.builder()
                .messageId(message.getMessageId())
                .mqType(message.getMqType())
                .topic(message.getTopic())
                .deadReasonType(analysisResult.getReasonType())
                .rootCause(analysisResult.getRootCause())
                .suggestedAction(analysisResult.getSuggestedAction())
                .riskLevel(determineRiskLevel(analysisResult))
                .analysisDetails(analysisResult.getDetails())
                .analysisTime(LocalDateTime.now())
                .build();
    }

    protected void postProcess(AnalysisResult result, DeadLetterMessage message) {
        Map<String, Object> details = result.getDetails() != null ? result.getDetails() : new HashMap<>();
        details.put("messageId", message.getMessageId());
        details.put("topic", message.getTopic());
        details.put("deadReason", message.getDeadReason());
        details.put("retryCount", message.getRetryCount());
        result.setDetails(details);
    }

    protected AlertLevelEnum determineRiskLevel(AnalysisResult result) {
        double confidence = result.getConfidence();
        if (confidence >= 0.9) {
            return AlertLevelEnum.CRITICAL;
        } else if (confidence >= 0.7) {
            return AlertLevelEnum.WARNING;
        } else if (confidence >= 0.5) {
            return AlertLevelEnum.INFO;
        }
        return getDefaultRiskLevel();
    }
}
