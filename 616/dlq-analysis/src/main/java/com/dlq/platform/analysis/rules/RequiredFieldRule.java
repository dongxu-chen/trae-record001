package com.dlq.platform.analysis.rules;

import com.dlq.platform.analysis.model.AnalysisResult;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.jeasy.rules.annotation.Action;
import org.jeasy.rules.annotation.Condition;
import org.jeasy.rules.annotation.Fact;
import org.jeasy.rules.annotation.Rule;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Slf4j
@Component
@Rule(name = "RequiredFieldRule", description = "必填字段校验规则", priority = 2)
public class RequiredFieldRule {

    private final ObjectMapper objectMapper = new ObjectMapper();

    private static final String[] REQUIRED_FIELDS = {"id", "orderId", "userId", "businessType", "timestamp"};

    @Condition
    public boolean checkRequiredFields(@Fact("message") DeadLetterMessage message) {
        String messageBody = message.getMessageBody();
        if (messageBody == null || messageBody.trim().isEmpty()) {
            return false;
        }
        try {
            JsonNode rootNode = objectMapper.readTree(messageBody);
            for (String field : REQUIRED_FIELDS) {
                if (!rootNode.has(field) || rootNode.get(field).isNull()) {
                    return true;
                }
            }
            return false;
        } catch (Exception e) {
            return false;
        }
    }

    @Action
    public void applyRule(@Fact("message") DeadLetterMessage message,
                        @Fact("result") AnalysisResult result) {
        String messageBody = message.getMessageBody();
        List<String> missingFields = new ArrayList<>();
        List<String> repairSteps = new ArrayList<>();

        try {
            JsonNode rootNode = objectMapper.readTree(messageBody);
            for (String field : REQUIRED_FIELDS) {
                if (!rootNode.has(field) || rootNode.get(field).isNull()) {
                    missingFields.add(field);
                }
            }
        } catch (Exception ignored) {
        }

        result.setRootCause("必填字段缺失: " + String.join(", ", missingFields));
        result.setSuggestedAction("补充缺失字段后重新发送消息");
        repairSteps.add("检查消息生成逻辑，确保所有必填字段被正确设置");
        repairSteps.add("补充缺失的字段值: " + String.join(", ", missingFields));
        repairSteps.add("验证数据完整性后重新发送消息");

        result.getDetails().put("ruleName", "RequiredFieldRule");
        result.getDetails().put("missingFields", missingFields);
        result.getDetails().put("requiredFields", List.of(REQUIRED_FIELDS));
        result.setConfidence(Math.max(result.getConfidence(), 0.85));
        result.setRepairSteps(repairSteps);
    }
}
