package com.dlq.platform.analysis.rules;

import com.dlq.platform.analysis.model.AnalysisResult;
import com.dlq.platform.analysis.utils.EncodingDetector;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.fasterxml.jackson.core.JsonParseException;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.jeasy.rules.annotation.Action;
import org.jeasy.rules.annotation.Condition;
import org.jeasy.rules.annotation.Fact;
import org.jeasy.rules.annotation.Rule;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

@Slf4j
@Component
@Rule(name = "JsonFormatRule", description = "JSON格式全面校验规则（含编码检测、Base64解码、格式修复）", priority = 1)
public class JsonFormatRule {

    private final ObjectMapper objectMapper = new ObjectMapper();

    private static final Pattern JSON_ARRAY_PATTERN = Pattern.compile("^\\s*\\[.*\\]\\s*$", Pattern.DOTALL);
    private static final Pattern JSON_OBJECT_PATTERN = Pattern.compile("^\\s*\\{.*\\}\\s*$", Pattern.DOTALL);
    private static final Pattern BASE64_PATTERN = Pattern.compile("^[A-Za-z0-9+/]*={0,2}$");

    @Condition
    public boolean checkJsonFormat(@Fact("message") DeadLetterMessage message) {
        String messageBody = message.getMessageBody();
        if (messageBody == null || messageBody.trim().isEmpty()) {
            return true;
        }

        if (tryParseWithAllEncodings(messageBody) != null) {
            return false;
        }

        return true;
    }

    @Action
    public void applyRule(@Fact("message") DeadLetterMessage message,
                        @Fact("result") AnalysisResult result) {
        String messageBody = message.getMessageBody();
        List<String> repairSteps = new ArrayList<>();
        double confidence = 0.9;

        result.getDetails().put("ruleName", "JsonFormatRule");
        result.getDetails().put("messageBodyLength", messageBody != null ? messageBody.length() : 0);

        if (messageBody == null || messageBody.trim().isEmpty()) {
            handleEmptyBody(result, repairSteps);
            confidence = 0.95;
        } else {
            FormatAnalysisResult analysis = analyzeFormatIssues(messageBody);
            applyAnalysisResult(result, analysis, repairSteps);
            confidence = analysis.confidence;
        }

        result.setConfidence(Math.max(result.getConfidence(), confidence));
        result.setRepairSteps(repairSteps);
    }

    private void handleEmptyBody(AnalysisResult result, List<String> repairSteps) {
        result.setRootCause("消息体为空");
        result.setSuggestedAction("检查生产者逻辑，确保消息体不为空");
        repairSteps.add("验证消息体是否被正确序列化");
        repairSteps.add("检查生产者是否正确设置消息体");
        repairSteps.add("确认消息发送前消息体已赋值");
        repairSteps.add("添加空消息体拦截检查");
    }

    private JsonNode tryParseWithAllEncodings(String messageBody) {
        List<EncodingDetector.EncodingResult> encodingResults = EncodingDetector.tryDecodeString(messageBody).getDecodedText() != null
                ? List.of(EncodingDetector.tryDecodeString(messageBody))
                : List.of();

        for (EncodingDetector.EncodingResult encodingResult : encodingResults) {
            if (encodingResult.isValid() && encodingResult.getDecodedText() != null) {
                try {
                    return objectMapper.readTree(encodingResult.getDecodedText());
                } catch (JsonProcessingException ignored) {
                }
            }
        }

        try {
            return objectMapper.readTree(messageBody);
        } catch (JsonProcessingException e) {
            return null;
        }
    }

    public static class FormatAnalysisResult {
        String rootCause;
        String suggestedAction;
        double confidence;
        String detectedEncoding;
        boolean isBase64Encoded;
        boolean hasEncodingIssues;
        List<String> repairSteps;
        Map<String, Object> details;

        public FormatAnalysisResult() {
            this.repairSteps = new ArrayList<>();
            this.details = new java.util.HashMap<>();
        }
    }

    private FormatAnalysisResult analyzeFormatIssues(String messageBody) {
        FormatAnalysisResult analysis = new FormatAnalysisResult();
        analysis.confidence = 0.8;

        checkEncodingIssues(messageBody, analysis);
        checkBase64Encoding(messageBody, analysis);

        String decodedBody = analysis.hasEncodingIssues && analysis.detectedEncoding != null
                ? EncodingDetector.detectAndConvert(messageBody)
                : messageBody;

        if (analysis.isBase64Encoded) {
            try {
                byte[] decoded = Base64.getDecoder().decode(messageBody.trim());
                decodedBody = new String(decoded);
                analysis.details.put("base64Decoded", true);
                analysis.details.put("decodedLength", decoded.length);
            } catch (Exception e) {
                analysis.details.put("base64DecodeError", e.getMessage());
            }
        }

        analyzeJsonSyntax(decodedBody, analysis);
        return analysis;
    }

    private void checkEncodingIssues(String messageBody, FormatAnalysisResult analysis) {
        EncodingDetector.EncodingResult encodingResult = EncodingDetector.tryDecodeString(messageBody);
        if (encodingResult != null && encodingResult.getCharset() != null
                && !encodingResult.getCharset().equals("UTF-8")
                && encodingResult.getConfidence() > 0.7) {
            analysis.hasEncodingIssues = true;
            analysis.detectedEncoding = encodingResult.getCharset();
            analysis.details.put("detectedEncoding", encodingResult.getCharset());
            analysis.details.put("encodingConfidence", encodingResult.getConfidence());
            analysis.repairSteps.add("检测到非UTF-8编码: " + encodingResult.getCharset());
            analysis.repairSteps.add("建议将消息编码转换为UTF-8");
        }

        if (EncodingDetector.isPotentialEncodingIssue(messageBody)) {
            analysis.hasEncodingIssues = true;
            analysis.details.put("hasGarbledCharacters", true);
            analysis.repairSteps.add("消息中存在乱码字符，请检查编码设置");
        }
    }

    private void checkBase64Encoding(String messageBody, FormatAnalysisResult analysis) {
        String trimmed = messageBody.trim();
        if (trimmed.length() > 10
                && trimmed.length() % 4 == 0
                && BASE64_PATTERN.matcher(trimmed).matches()) {
            try {
                byte[] decoded = Base64.getDecoder().decode(trimmed);
                String decodedStr = new String(decoded);
                if (looksLikeJson(decodedStr)) {
                    analysis.isBase64Encoded = true;
                    analysis.details.put("base64Encoded", true);
                    analysis.repairSteps.add("检测到Base64编码的JSON消息");
                    analysis.repairSteps.add("请先Base64解码后再处理");
                }
            } catch (Exception ignored) {
            }
        }
    }

    private boolean looksLikeJson(String str) {
        if (str == null || str.isEmpty()) return false;
        String trimmed = str.trim();
        return JSON_OBJECT_PATTERN.matcher(trimmed).matches()
                || JSON_ARRAY_PATTERN.matcher(trimmed).matches();
    }

    private void analyzeJsonSyntax(String jsonBody, FormatAnalysisResult analysis) {
        if (jsonBody == null) return;

        try {
            objectMapper.readTree(jsonBody);
            analysis.rootCause = "消息格式校验通过，但业务处理失败";
            analysis.suggestedAction = "请检查业务逻辑处理流程";
            analysis.repairSteps.add("验证业务逻辑是否正确处理消息");
            analysis.repairSteps.add("检查消息字段是否符合业务预期");
            analysis.confidence = 0.6;
            return;
        } catch (JsonParseException e) {
            analyzeJsonParseException(e, jsonBody, analysis);
        } catch (JsonProcessingException e) {
            analysis.rootCause = "JSON格式错误: " + e.getOriginalMessage();
            analysis.suggestedAction = "修复JSON格式错误后重发消息";
            analysis.repairSteps.add("使用JSON校验工具验证消息格式");
            analysis.repairSteps.add("检查特殊字符转义");
            analysis.repairSteps.add("修复格式错误后重新发送");
        }
    }

    private void analyzeJsonParseException(JsonParseException e, String jsonBody, FormatAnalysisResult analysis) {
        analysis.rootCause = "JSON语法错误: " + e.getOriginalMessage();
        analysis.details.put("errorType", "syntax");

        if (e.getLocation() != null) {
            analysis.details.put("errorLine", e.getLocation().getLineNr());
            analysis.details.put("errorColumn", e.getLocation().getColumnNr());
            analysis.details.put("errorOffset", e.getLocation().getCharOffset());
        }

        String errorMsg = e.getOriginalMessage();
        if (errorMsg != null) {
            if (errorMsg.contains("Unexpected character")) {
                analysis.suggestedAction = "存在意外字符，请检查消息内容是否有非法字符";
                analysis.repairSteps.add("检查消息中是否包含非法控制字符");
                analysis.repairSteps.add("检查编码转换是否正确");
                analysis.repairSteps.add("使用转义字符处理特殊字符");
            } else if (errorMsg.contains("Unrecognized token")) {
                analysis.suggestedAction = "存在未识别的标记，请检查引号是否正确闭合";
                analysis.repairSteps.add("检查属性名称是否用双引号包裹");
                analysis.repairSteps.add("检查字符串是否正确闭合");
                analysis.repairSteps.add("检查逗号分隔符是否正确");
            } else if (errorMsg.contains("Unexpected end-of-input")) {
                analysis.suggestedAction = "JSON不完整，可能被截断";
                analysis.repairSteps.add("检查消息是否完整传输");
                analysis.repairSteps.add("检查消息大小限制配置");
                analysis.repairSteps.add("验证消息生成逻辑");
            } else if (errorMsg.contains("Expected a colon")) {
                analysis.suggestedAction = "缺少冒号分隔符";
                analysis.repairSteps.add("检查键值对格式是否正确");
                analysis.repairSteps.add("检查冒号前后是否有多余字符");
            } else {
                analysis.suggestedAction = "修复JSON语法错误后重新发送";
                analysis.repairSteps.add("使用在线JSON校验工具定位错误");
                analysis.repairSteps.add("检查消息体是否被意外修改");
            }
        }

        analysis.repairSteps.add("修复格式错误后重新发送消息");
        analysis.confidence = 0.9;
    }

    private void applyAnalysisResult(AnalysisResult result, FormatAnalysisResult analysis, List<String> repairSteps) {
        result.setRootCause(analysis.rootCause);
        result.setSuggestedAction(analysis.suggestedAction);
        result.getDetails().putAll(analysis.details);
        repairSteps.addAll(analysis.repairSteps);
    }
}
