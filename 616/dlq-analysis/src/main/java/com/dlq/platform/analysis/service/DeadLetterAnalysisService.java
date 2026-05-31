package com.dlq.platform.analysis.service;

import com.dlq.platform.analysis.analyzer.DeadLetterAnalyzer;
import com.dlq.platform.analysis.generator.SuggestionGenerator;
import com.dlq.platform.analysis.model.AnalysisResult;
import com.dlq.platform.common.dto.DeadLetterAnalysisResult;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.AlertLevelEnum;
import com.dlq.platform.common.enums.DeadReasonTypeEnum;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class DeadLetterAnalysisService {

    private final List<DeadLetterAnalyzer> analyzers;
    private final SuggestionGenerator suggestionGenerator;

    public List<DeadLetterAnalysisResult> analyzeBatch(List<DeadLetterMessage> messages) {
        return messages.stream()
                .map(this::analyze)
                .filter(Objects::nonNull)
                .collect(Collectors.toList());
    }

    public DeadLetterAnalysisResult analyze(DeadLetterMessage message) {
        log.info("开始分析死信消息, messageId: {}, topic: {}", message.getMessageId(), message.getTopic());

        try {
            List<AnalysisResult> results = new ArrayList<>();

            for (DeadLetterAnalyzer analyzer : analyzers) {
                if (analyzer.support(message)) {
                    log.debug("使用分析器 {} 分析消息 {}", analyzer.getClass().getSimpleName(), message.getMessageId());
                    AnalysisResult result = analyzer.analyze(message);
                    if (result != null && result.getConfidence() > 0) {
                        results.add(result);
                    }
                }
            }

            if (results.isEmpty()) {
                log.warn("没有匹配的分析器，使用默认分析, messageId: {}", message.getMessageId());
                return buildDefaultResult(message);
            }

            AnalysisResult bestResult = selectBestResult(results);
            suggestionGenerator.enhanceSuggestion(bestResult);

            DeadLetterAnalysisResult finalResult = convertToDto(message, bestResult);
            finalResult.setAnalysisDetails(mergeAnalysisDetails(results, bestResult));

            log.info("死信消息分析完成, messageId: {}, reasonType: {}, confidence: {}",
                    message.getMessageId(), bestResult.getReasonType(), bestResult.getConfidence());

            return finalResult;
        } catch (Exception e) {
            log.error("分析死信消息异常, messageId: {}", message.getMessageId(), e);
            return buildErrorResult(message, e);
        }
    }

    public Map<String, DeadLetterAnalysisResult> analyzeToMap(List<DeadLetterMessage> messages) {
        Map<String, DeadLetterAnalysisResult> resultMap = new HashMap<>();
        for (DeadLetterMessage message : messages) {
            DeadLetterAnalysisResult result = analyze(message);
            if (result != null && result.getMessageId() != null) {
                resultMap.put(result.getMessageId(), result);
            }
        }
        return resultMap;
    }

    public Map<DeadReasonTypeEnum, List<DeadLetterAnalysisResult>> groupByReasonType(List<DeadLetterMessage> messages) {
        List<DeadLetterAnalysisResult> results = analyzeBatch(messages);
        return results.stream()
                .collect(Collectors.groupingBy(
                        r -> r.getDeadReasonType() != null ? r.getDeadReasonType() : DeadReasonTypeEnum.OTHER
                ));
    }

    public Map<String, Object> getAnalysisStatistics(List<DeadLetterMessage> messages) {
        Map<String, Object> stats = new HashMap<>();
        List<DeadLetterAnalysisResult> results = analyzeBatch(messages);

        stats.put("totalCount", messages.size());
        stats.put("analyzedCount", results.size());

        Map<DeadReasonTypeEnum, Long> reasonCounts = results.stream()
                .collect(Collectors.groupingBy(
                        r -> r.getDeadReasonType() != null ? r.getDeadReasonType() : DeadReasonTypeEnum.OTHER,
                        Collectors.counting()
                ));
        stats.put("reasonDistribution", reasonCounts);

        Map<AlertLevelEnum, Long> riskCounts = results.stream()
                .collect(Collectors.groupingBy(
                        r -> r.getRiskLevel() != null ? r.getRiskLevel() : AlertLevelEnum.LOW,
                        Collectors.counting()
                ));
        stats.put("riskDistribution", riskCounts);

        double avgConfidence = results.stream()
                .mapToDouble(r -> {
                    Map<String, Object> details = r.getAnalysisDetails();
                    if (details != null && details.containsKey("confidence")) {
                        return ((Number) details.get("confidence")).doubleValue();
                    }
                    return 0.5;
                })
                .average()
                .orElse(0.0);
        stats.put("averageConfidence", avgConfidence);

        return stats;
    }

    private AnalysisResult selectBestResult(List<AnalysisResult> results) {
        return results.stream()
                .max(Comparator.comparingDouble(AnalysisResult::getConfidence)
                        .thenComparing(r -> r.getReasonType() != null ? r.getReasonType().ordinal() : Integer.MAX_VALUE))
                .orElse(null);
    }

    private DeadLetterAnalysisResult convertToDto(DeadLetterMessage message, AnalysisResult result) {
        AlertLevelEnum riskLevel = determineRiskLevel(result.getConfidence());

        return DeadLetterAnalysisResult.builder()
                .messageId(message.getMessageId())
                .mqType(message.getMqType())
                .topic(message.getTopic())
                .deadReasonType(result.getReasonType())
                .rootCause(result.getRootCause())
                .suggestedAction(result.getSuggestedAction())
                .riskLevel(riskLevel)
                .analysisDetails(buildAnalysisDetails(message, result))
                .analysisTime(LocalDateTime.now())
                .build();
    }

    private Map<String, Object> buildAnalysisDetails(DeadLetterMessage message, AnalysisResult result) {
        Map<String, Object> details = new HashMap<>();
        details.put("confidence", result.getConfidence());
        details.put("repairSteps", result.getRepairSteps());
        details.put("retryCount", message.getRetryCount());
        details.put("deadReason", message.getDeadReason());

        if (result.getDetails() != null) {
            details.putAll(result.getDetails());
        }

        if (result.getRepairSteps() != null && !result.getRepairSteps().isEmpty()) {
            details.put("detailedSuggestion", suggestionGenerator.generateDetailedSuggestion(result));
        }

        return details;
    }

    private Map<String, Object> mergeAnalysisDetails(List<AnalysisResult> allResults, AnalysisResult bestResult) {
        Map<String, Object> details = new HashMap<>();
        details.put("matchedAnalyzers", allResults.size());

        List<Map<String, Object>> allMatchDetails = allResults.stream()
                .map(r -> {
                    Map<String, Object> m = new HashMap<>();
                    m.put("reasonType", r.getReasonType() != null ? r.getReasonType().getCode() : "UNKNOWN");
                    m.put("confidence", r.getConfidence());
                    m.put("rootCause", r.getRootCause());
                    return m;
                })
                .collect(Collectors.toList());
        details.put("allMatches", allMatchDetails);

        if (bestResult.getDetails() != null) {
            details.putAll(bestResult.getDetails());
        }

        return details;
    }

    private DeadLetterAnalysisResult buildDefaultResult(DeadLetterMessage message) {
        AnalysisResult defaultResult = AnalysisResult.builder()
                .reasonType(DeadReasonTypeEnum.OTHER)
                .confidence(0.1)
                .rootCause("无法自动识别死信原因")
                .suggestedAction("请人工介入分析")
                .repairSteps(List.of(
                        "1. 查看消息详细内容和死信原因",
                        "2. 分析相关系统日志",
                        "3. 根据具体情况进行处理"
                ))
                .details(new HashMap<>())
                .build();

        return DeadLetterAnalysisResult.builder()
                .messageId(message.getMessageId())
                .mqType(message.getMqType())
                .topic(message.getTopic())
                .deadReasonType(DeadReasonTypeEnum.OTHER)
                .rootCause(defaultResult.getRootCause())
                .suggestedAction(defaultResult.getSuggestedAction())
                .riskLevel(AlertLevelEnum.INFO)
                .analysisDetails(buildAnalysisDetails(message, defaultResult))
                .analysisTime(LocalDateTime.now())
                .build();
    }

    private DeadLetterAnalysisResult buildErrorResult(DeadLetterMessage message, Exception e) {
        return DeadLetterAnalysisResult.builder()
                .messageId(message.getMessageId())
                .mqType(message.getMqType())
                .topic(message.getTopic())
                .deadReasonType(DeadReasonTypeEnum.OTHER)
                .rootCause("分析过程发生异常: " + e.getMessage())
                .suggestedAction("请检查分析服务状态")
                .riskLevel(AlertLevelEnum.MEDIUM)
                .analysisDetails(Map.of(
                        "error", e.getMessage(),
                        "errorType", e.getClass().getName()
                ))
                .analysisTime(LocalDateTime.now())
                .build();
    }

    private AlertLevelEnum determineRiskLevel(double confidence) {
        if (confidence >= 0.9) {
            return AlertLevelEnum.CRITICAL;
        } else if (confidence >= 0.7) {
            return AlertLevelEnum.MEDIUM;
        } else {
            return AlertLevelEnum.LOW;
        }
    }
}
