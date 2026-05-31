package com.dlq.platform.analysis.auto;

import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.DeadReasonTypeEnum;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Service
@RequiredArgsConstructor
public class AutoRepairService {

    private final ObjectMapper objectMapper = new ObjectMapper();

    public static class RepairResult {
        private boolean repaired;
        private String repairedBody;
        private String repairType;
        private List<String> repairSteps;
        private double confidence;
        private String originalError;

        public RepairResult() {
            this.repairSteps = new ArrayList<>();
            this.confidence = 0.0;
        }

        public boolean isRepaired() { return repaired; }
        public void setRepaired(boolean repaired) { this.repaired = repaired; }
        public String getRepairedBody() { return repairedBody; }
        public void setRepairedBody(String repairedBody) { this.repairedBody = repairedBody; }
        public String getRepairType() { return repairType; }
        public void setRepairType(String repairType) { this.repairType = repairType; }
        public List<String> getRepairSteps() { return repairSteps; }
        public void setRepairSteps(List<String> repairSteps) { this.repairSteps = repairSteps; }
        public double getConfidence() { return confidence; }
        public void setConfidence(double confidence) { this.confidence = confidence; }
        public String getOriginalError() { return originalError; }
        public void setOriginalError(String originalError) { this.originalError = originalError; }
    }

    public RepairResult tryAutoRepair(DeadLetterMessage message) {
        RepairResult result = new RepairResult();

        if (message.getDeadReasonType() != DeadReasonTypeEnum.FORMAT_ERROR) {
            return result;
        }

        String messageBody = message.getMessageBody();
        if (messageBody == null) {
            return result;
        }

        try {
            objectMapper.readTree(messageBody);
            result.setRepaired(true);
            result.setRepairedBody(messageBody);
            result.setRepairType("NO_REPAIR_NEEDED");
            result.setConfidence(1.0);
            return result;
        } catch (JsonProcessingException e) {
            result.setOriginalError(e.getOriginalMessage());
        }

        List<RepairStrategy> strategies = Arrays.asList(
                this::repairEncoding,
                this::repairBase64EncodedJson,
                this::repairSingleQuotes,
                this::repairUnquotedKeys,
                this::repairTrailingCommas,
                this::repairMissingBraces,
                this::repairMissingQuotes,
                this::repairEscapeCharacters
        );

        for (RepairStrategy strategy : strategies) {
            try {
                RepairStrategyResult strategyResult = strategy.repair(messageBody);
                if (strategyResult.success) {
                    result.setRepaired(true);
                    result.setRepairedBody(strategyResult.body);
                    result.setRepairType(strategyResult.type);
                    result.getRepairSteps().addAll(strategyResult.steps);
                    result.setConfidence(strategyResult.confidence);
                    log.info("自动修复成功, messageId: {}, 修复类型: {}", message.getId(), strategyResult.type);
                    return result;
                }
            } catch (Exception e) {
                log.debug("修复策略执行失败, type: {}", strategy.getClass().getSimpleName(), e);
            }
        }

        RepairStrategyResult combinedResult = tryCombinedRepair(messageBody);
        if (combinedResult.success) {
            result.setRepaired(true);
            result.setRepairedBody(combinedResult.body);
            result.setRepairType(combinedResult.type);
            result.getRepairSteps().addAll(combinedResult.steps);
            result.setConfidence(combinedResult.confidence);
            log.info("组合修复成功, messageId: {}, 修复类型: {}", message.getId(), combinedResult.type);
        }

        return result;
    }

    @FunctionalInterface
    private interface RepairStrategy {
        RepairStrategyResult repair(String body) throws Exception;
    }

    private static class RepairStrategyResult {
        boolean success;
        String body;
        String type;
        List<String> steps;
        double confidence;

        RepairStrategyResult() {
            this.steps = new ArrayList<>();
        }
    }

    private RepairStrategyResult repairEncoding(String body) {
        RepairStrategyResult result = new RepairStrategyResult();
        try {
            byte[] bytes = body.getBytes("ISO-8859-1");
            String decoded = new String(bytes, "UTF-8");
            
            if (!decoded.equals(body)) {
                try {
                    objectMapper.readTree(decoded);
                    result.success = true;
                    result.body = decoded;
                    result.type = "ENCODING_FIXED";
                    result.confidence = 0.8;
                    result.steps.add("检测到编码问题，将ISO-8859-1转换为UTF-8");
                } catch (JsonProcessingException ignored) {
                }
            }
        } catch (Exception e) {
            log.debug("编码修复失败", e);
        }
        return result;
    }

    private RepairStrategyResult repairBase64EncodedJson(String body) {
        RepairStrategyResult result = new RepairStrategyResult();
        String trimmed = body.trim();
        
        if (trimmed.length() > 10 && trimmed.length() % 4 == 0
                && trimmed.matches("^[A-Za-z0-9+/]*={0,2}$")) {
            try {
                byte[] decoded = Base64.getDecoder().decode(trimmed);
                String decodedStr = new String(decoded);
                objectMapper.readTree(decodedStr);
                
                result.success = true;
                result.body = decodedStr;
                result.type = "BASE64_DECODED";
                result.confidence = 0.9;
                result.steps.add("检测到Base64编码，解码后为有效的JSON");
            } catch (Exception ignored) {
            }
        }
        return result;
    }

    private RepairStrategyResult repairSingleQuotes(String body) {
        RepairStrategyResult result = new RepairStrategyResult();
        if (!body.contains("'")) {
            return result;
        }

        String replaced = body.replaceAll("(?<!\\\\)'", "\"");
        try {
            objectMapper.readTree(replaced);
            result.success = true;
            result.body = replaced;
            result.type = "SINGLE_QUOTES_FIXED";
            result.confidence = 0.7;
            result.steps.add("将单引号替换为双引号");
        } catch (JsonProcessingException ignored) {
        }
        return result;
    }

    private RepairStrategyResult repairUnquotedKeys(String body) {
        RepairStrategyResult result = new RepairStrategyResult();
        
        Pattern pattern = Pattern.compile("(\\{|,|\\[)\\s*([a-zA-Z_][a-zA-Z0-9_]*)\\s*:");
        Matcher matcher = pattern.matcher(body);
        StringBuffer sb = new StringBuffer();
        
        while (matcher.find()) {
            String prefix = matcher.group(1);
            String key = matcher.group(2);
            if (!isReservedWord(key)) {
                matcher.appendReplacement(sb, Matcher.quoteReplacement(prefix + "\"" + key + "\":"));
            }
        }
        matcher.appendTail(sb);
        
        String fixed = sb.toString();
        if (!fixed.equals(body)) {
            try {
                objectMapper.readTree(fixed);
                result.success = true;
                result.body = fixed;
                result.type = "UNQUOTED_KEYS_FIXED";
                result.confidence = 0.6;
                result.steps.add("为未加引号的JSON键添加双引号");
            } catch (JsonProcessingException ignored) {
            }
        }
        return result;
    }

    private RepairStrategyResult repairTrailingCommas(String body) {
        RepairStrategyResult result = new RepairStrategyResult();
        
        String fixed = body.replaceAll(",\\s*([}\\]])", "$1");
        
        if (!fixed.equals(body)) {
            try {
                objectMapper.readTree(fixed);
                result.success = true;
                result.body = fixed;
                result.type = "TRAILING_COMMAS_FIXED";
                result.confidence = 0.8;
                result.steps.add("移除对象/数组末尾的多余逗号");
            } catch (JsonProcessingException ignored) {
            }
        }
        return result;
    }

    private RepairStrategyResult repairMissingBraces(String body) {
        RepairStrategyResult result = new RepairStrategyResult();
        String trimmed = body.trim();
        
        String fixed = trimmed;
        int openBraces = countOccurrences(trimmed, '{');
        int closeBraces = countOccurrences(trimmed, '}');
        
        if (openBraces > closeBraces) {
            fixed = trimmed + "}".repeat(openBraces - closeBraces);
        } else if (closeBraces > openBraces) {
            fixed = "{".repeat(closeBraces - openBraces) + trimmed;
        }
        
        if (!fixed.equals(trimmed)) {
            try {
                objectMapper.readTree(fixed);
                result.success = true;
                result.body = fixed;
                result.type = "MISSING_BRACES_FIXED";
                result.confidence = 0.5;
                result.steps.add(String.format("补全缺失的括号: 缺少%d个", Math.abs(openBraces - closeBraces)));
            } catch (JsonProcessingException ignored) {
            }
        }
        return result;
    }

    private RepairStrategyResult repairMissingQuotes(String body) {
        RepairStrategyResult result = new RepairStrategyResult();
        
        Pattern pattern = Pattern.compile(":([^{}\\[\\],\\s\"]+)([,}\\]])");
        Matcher matcher = pattern.matcher(body);
        StringBuffer sb = new StringBuffer();
        
        while (matcher.find()) {
            String value = matcher.group(1);
            String suffix = matcher.group(2);
            if (!isNumeric(value) && !isBoolean(value) && !value.equals("null")) {
                matcher.appendReplacement(sb, Matcher.quoteReplacement(":\"" + value + "\"" + suffix));
            }
        }
        matcher.appendTail(sb);
        
        String fixed = sb.toString();
        if (!fixed.equals(body)) {
            try {
                objectMapper.readTree(fixed);
                result.success = true;
                result.body = fixed;
                result.type = "MISSING_VALUE_QUOTES_FIXED";
                result.confidence = 0.5;
                result.steps.add("为未加引号的字符串值添加双引号");
            } catch (JsonProcessingException ignored) {
            }
        }
        return result;
    }

    private RepairStrategyResult repairEscapeCharacters(String body) {
        RepairStrategyResult result = new RepairStrategyResult();
        
        String fixed = body
                .replaceAll("(?<!\\\\)\\\\([^\"\\\\/bfnrtu])", "\\\\\\\\$1")
                .replaceAll("(?<!\\\\)\"(?=\\s*[a-zA-Z])", "\\\\\"");
        
        if (!fixed.equals(body)) {
            try {
                objectMapper.readTree(fixed);
                result.success = true;
                result.body = fixed;
                result.type = "ESCAPE_CHARS_FIXED";
                result.confidence = 0.4;
                result.steps.add("修复转义字符问题");
            } catch (JsonProcessingException ignored) {
            }
        }
        return result;
    }

    private RepairStrategyResult tryCombinedRepair(String body) {
        RepairStrategyResult result = new RepairStrategyResult();
        String current = body;
        List<String> steps = new ArrayList<>();
        
        current = current.replaceAll("(?<!\\\\)'", "\"");
        if (!current.equals(body)) steps.add("替换单引号为双引号");
        
        Pattern keyPattern = Pattern.compile("(\\{|,|\\[)\\s*([a-zA-Z_][a-zA-Z0-9_]*)\\s*:");
        Matcher keyMatcher = keyPattern.matcher(current);
        StringBuffer keySb = new StringBuffer();
        while (keyMatcher.find()) {
            String prefix = keyMatcher.group(1);
            String key = keyMatcher.group(2);
            if (!isReservedWord(key)) {
                keyMatcher.appendReplacement(keySb, Matcher.quoteReplacement(prefix + "\"" + key + "\":"));
            }
        }
        keyMatcher.appendTail(keySb);
        if (!keySb.toString().equals(current)) {
            steps.add("为JSON键添加引号");
            current = keySb.toString();
        }
        
        current = current.replaceAll(",\\s*([}\\]])", "$1");
        if (!current.equals(keySb.toString())) steps.add("移除多余逗号");
        
        try {
            objectMapper.readTree(current);
            result.success = true;
            result.body = current;
            result.type = "COMBINED_FIX";
            result.confidence = 0.4;
            result.steps = steps;
        } catch (JsonProcessingException ignored) {
        }
        
        return result;
    }

    private boolean isReservedWord(String word) {
        return word.equals("true") || word.equals("false") || word.equals("null");
    }

    private boolean isNumeric(String str) {
        try {
            Double.parseDouble(str);
            return true;
        } catch (NumberFormatException e) {
            return false;
        }
    }

    private boolean isBoolean(String str) {
        return "true".equals(str) || "false".equals(str);
    }

    private int countOccurrences(String str, char c) {
        int count = 0;
        for (int i = 0; i < str.length(); i++) {
            if (str.charAt(i) == c) count++;
        }
        return count;
    }

    public Map<String, Object> getRepairCapabilities() {
        Map<String, Object> capabilities = new HashMap<>();
        
        List<Map<String, Object>> strategies = new ArrayList<>();
        strategies.add(createStrategy("ENCODING_FIXED", "编码修复", "检测并修复编码问题（ISO-8859-1转UTF-8）", 0.8));
        strategies.add(createStrategy("BASE64_DECODED", "Base64解码", "自动检测并解码Base64编码的JSON", 0.9));
        strategies.add(createStrategy("SINGLE_QUOTES_FIXED", "单引号修复", "将单引号替换为标准JSON双引号", 0.7));
        strategies.add(createStrategy("UNQUOTED_KEYS_FIXED", "键名引号修复", "为未加引号的JSON键添加双引号", 0.6));
        strategies.add(createStrategy("TRAILING_COMMAS_FIXED", "尾逗号修复", "移除对象/数组末尾的多余逗号", 0.8));
        strategies.add(createStrategy("MISSING_BRACES_FIXED", "括号补全", "检测并补全缺失的大括号", 0.5));
        strategies.add(createStrategy("MISSING_VALUE_QUOTES_FIXED", "值引号修复", "为字符串值添加缺失的双引号", 0.5));
        strategies.add(createStrategy("ESCAPE_CHARS_FIXED", "转义字符修复", "修复转义字符问题", 0.4));
        strategies.add(createStrategy("COMBINED_FIX", "组合修复", "应用多种修复策略组合", 0.4));
        
        capabilities.put("strategies", strategies);
        capabilities.put("totalStrategies", strategies.size());
        capabilities.put("autoReplayEnabled", true);
        capabilities.put("minConfidenceForAutoReplay", 0.7);
        
        return capabilities;
    }

    private Map<String, Object> createStrategy(String type, String name, String description, double confidence) {
        Map<String, Object> strategy = new HashMap<>();
        strategy.put("type", type);
        strategy.put("name", name);
        strategy.put("description", description);
        strategy.put("confidence", confidence);
        return strategy;
    }
}
