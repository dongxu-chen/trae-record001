package com.dlq.platform.service;

import com.dlq.platform.analysis.auto.AutoRepairService;
import com.dlq.platform.analysis.prediction.DeadLetterPredictionService;
import com.dlq.platform.analysis.visualization.DeadLetterVisualizationService;
import com.dlq.platform.common.dto.DeadLetterQueryDTO;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.DeadReasonTypeEnum;
import com.dlq.platform.common.enums.MqTypeEnum;
import com.dlq.platform.es.service.DeadLetterEsService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class DeadLetterAnalyticsService {

    private final DeadLetterPredictionService predictionService;
    private final AutoRepairService autoRepairService;
    private final DeadLetterVisualizationService visualizationService;
    private final DeadLetterEsService deadLetterEsService;
    private final DeadLetterReplayService replayService;

    public Map<String, Object> predictDeadLetterTrend(
            String topic,
            MqTypeEnum mqType,
            int forecastDays,
            LocalDateTime startTime,
            LocalDateTime endTime) {

        Map<String, Object> result = new HashMap<>();

        try {
            DeadLetterQueryDTO query = DeadLetterQueryDTO.builder()
                    .topic(topic)
                    .mqType(mqType)
                    .startTime(startTime)
                    .endTime(endTime)
                    .pageNum(1)
                    .pageSize(10000)
                    .build();

            Map<String, Object> queryResult = deadLetterEsService.query(query);
            List<DeadLetterMessage> messages = (List<DeadLetterMessage>) queryResult.get("list");

            if (messages == null || messages.isEmpty()) {
                result.put("success", false);
                result.put("message", "没有足够的历史数据进行预测");
                return result;
            }

            Map<LocalDateTime, Long> dailyCounts = messages.stream()
                    .collect(Collectors.groupingBy(
                            msg -> msg.getCreateTime() != null ? msg.getCreateTime().toLocalDate().atStartOfDay() : LocalDateTime.now(),
                            Collectors.counting()
                    ));

            List<DeadLetterPredictionService.TimeSeriesData> timeSeriesData = dailyCounts.entrySet().stream()
                    .map(entry -> new DeadLetterPredictionService.TimeSeriesData(entry.getKey(), entry.getValue()))
                    .collect(Collectors.toList());

            DeadLetterPredictionService.PredictionResult predictionResult =
                    predictionService.predict(timeSeriesData, forecastDays);

            Map<String, Object> forecastReport = predictionService.generateForecastReport(predictionResult);

            result.put("success", true);
            result.put("data", forecastReport);
            result.put("historicalDataPoints", timeSeriesData.size());

            log.info("死信趋势预测完成, 预测天数: {}, 历史数据点: {}", forecastDays, timeSeriesData.size());

        } catch (Exception e) {
            log.error("死信趋势预测异常", e);
            result.put("success", false);
            result.put("message", "预测异常: " + e.getMessage());
        }

        return result;
    }

    public Map<String, Object> tryAutoRepairAndReplay(String messageId, boolean autoReplay) {
        Map<String, Object> result = new HashMap<>();

        try {
            DeadLetterMessage message = deadLetterEsService.findById(messageId);
            if (message == null) {
                result.put("success", false);
                result.put("message", "死信消息不存在, id: " + messageId);
                return result;
            }

            AutoRepairService.RepairResult repairResult = autoRepairService.tryAutoRepair(message);
            result.put("repaired", repairResult.isRepaired());
            result.put("repairType", repairResult.getRepairType());
            result.put("repairSteps", repairResult.getRepairSteps());
            result.put("confidence", repairResult.getConfidence());
            result.put("originalError", repairResult.getOriginalError());

            if (repairResult.isRepaired()) {
                result.put("repairedBody", repairResult.getRepairedBody());

                if (autoReplay && repairResult.getConfidence() >= 0.7) {
                    message.setMessageBody(repairResult.getRepairedBody());
                    if (message.getHeaders() == null) {
                        message.setHeaders(new HashMap<>());
                    }
                    message.getHeaders().put("autoRepairType", repairResult.getRepairType());
                    message.getHeaders().put("autoRepairSteps", String.join("; ", repairResult.getRepairSteps()));
                    message.getHeaders().put("autoRepairConfidence", String.valueOf(repairResult.getConfidence()));
                    deadLetterEsService.save(message);

                    Map<String, Object> replayResult = replayService.replaySingle(messageId, null);
                    result.put("autoReplayResult", replayResult);

                    log.info("自动修复并重放成功, messageId: {}, 修复类型: {}", messageId, repairResult.getRepairType());
                } else if (autoReplay) {
                    result.put("autoReplaySkipped", true);
                    result.put("skipReason", "置信度低于阈值: " + repairResult.getConfidence() + " < 0.7");
                }
            }

            result.put("success", true);
            log.info("自动修复完成, messageId: {}, 修复成功: {}", messageId, repairResult.isRepaired());

        } catch (Exception e) {
            log.error("自动修复异常, messageId: {}", messageId, e);
            result.put("success", false);
            result.put("message", "自动修复异常: " + e.getMessage());
        }

        return result;
    }

    public Map<String, Object> batchAutoRepair(List<String> messageIds, boolean autoReplay) {
        Map<String, Object> result = new HashMap<>();
        List<Map<String, Object>> results = new ArrayList<>();

        int successCount = 0;
        int repairedCount = 0;
        int replayedCount = 0;

        for (String messageId : messageIds) {
            try {
                Map<String, Object> repairResult = tryAutoRepairAndReplay(messageId, autoReplay);
                results.add(repairResult);

                if (Boolean.TRUE.equals(repairResult.get("success"))) {
                    successCount++;
                }
                if (Boolean.TRUE.equals(repairResult.get("repaired"))) {
                    repairedCount++;
                }
                if (repairResult.containsKey("autoReplayResult")) {
                    replayedCount++;
                }
            } catch (Exception e) {
                log.error("批量自动修复异常, messageId: {}", messageId, e);
            }
        }

        result.put("success", true);
        result.put("totalCount", messageIds.size());
        result.put("successCount", successCount);
        result.put("repairedCount", repairedCount);
        result.put("replayedCount", replayedCount);
        result.put("results", results);

        log.info("批量自动修复完成, 总数: {}, 修复成功: {}, 重放: {}", messageIds.size(), repairedCount, replayedCount);
        return result;
    }

    public Map<String, Object> getVisualizationData(
            String type,
            String topic,
            MqTypeEnum mqType,
            String interval,
            LocalDateTime startTime,
            LocalDateTime endTime) {

        Map<String, Object> result = new HashMap<>();

        try {
            DeadLetterQueryDTO query = DeadLetterQueryDTO.builder()
                    .topic(topic)
                    .mqType(mqType)
                    .startTime(startTime)
                    .endTime(endTime)
                    .pageNum(1)
                    .pageSize(10000)
                    .build();

            Map<String, Object> queryResult = deadLetterEsService.query(query);
            List<DeadLetterMessage> messages = (List<DeadLetterMessage>) queryResult.get("list");

            if (messages == null || messages.isEmpty()) {
                result.put("success", false);
                result.put("message", "没有数据");
                return result;
            }

            switch (type.toLowerCase()) {
                case "timeline":
                    result = generateTimelineData(messages, interval);
                    break;
                case "heatmap":
                    result = generateHeatmapData(messages);
                    break;
                case "topic_heatmap":
                    result = generateTopicHeatmapData(messages);
                    break;
                case "sankey":
                    result = generateSankeyData(messages);
                    break;
                case "all":
                    result = generateAllVisualizations(messages, interval);
                    break;
                default:
                    result.put("success", false);
                    result.put("message", "不支持的可视化类型: " + type);
            }

            log.info("可视化数据生成完成, 类型: {}, 数据量: {}", type, messages.size());

        } catch (Exception e) {
            log.error("生成可视化数据异常", e);
            result.put("success", false);
            result.put("message", "生成可视化数据异常: " + e.getMessage());
        }

        return result;
    }

    private Map<String, Object> generateTimelineData(List<DeadLetterMessage> messages, String interval) {
        Map<String, Object> result = new HashMap<>();

        Map<LocalDateTime, Long> timeData = messages.stream()
                .collect(Collectors.groupingBy(
                        msg -> msg.getCreateTime() != null ? msg.getCreateTime() : LocalDateTime.now(),
                        Collectors.counting()
                ));

        DeadLetterVisualizationService.TimelineResult timeline =
                visualizationService.generateTimeline(timeData, interval, true, null);

        result.put("success", true);
        result.put("data", timeline);
        return result;
    }

    private Map<String, Object> generateHeatmapData(List<DeadLetterMessage> messages) {
        Map<String, Object> result = new HashMap<>();

        Map<LocalDateTime, Long> timeData = messages.stream()
                .collect(Collectors.groupingBy(
                        msg -> msg.getCreateTime() != null ? msg.getCreateTime() : LocalDateTime.now(),
                        Collectors.counting()
                ));

        DeadLetterVisualizationService.HeatmapData heatmap =
                visualizationService.generateHourlyHeatmap(timeData);

        result.put("success", true);
        result.put("data", heatmap);
        return result;
    }

    private Map<String, Object> generateTopicHeatmapData(List<DeadLetterMessage> messages) {
        Map<String, Object> result = new HashMap<>();

        List<String> topics = messages.stream()
                .map(DeadLetterMessage::getTopic)
                .filter(Objects::nonNull)
                .distinct()
                .collect(Collectors.toList());

        Map<String, Map<LocalDateTime, Long>> topicData = new HashMap<>();
        for (String topic : topics) {
            Map<LocalDateTime, Long> timeData = messages.stream()
                    .filter(m -> topic.equals(m.getTopic()))
                    .collect(Collectors.groupingBy(
                            msg -> msg.getCreateTime() != null ? msg.getCreateTime() : LocalDateTime.now(),
                            Collectors.counting()
                    ));
            topicData.put(topic, timeData);
        }

        DeadLetterVisualizationService.HeatmapData heatmap =
                visualizationService.generateTopicHeatmap(topics, topicData);

        result.put("success", true);
        result.put("data", heatmap);
        return result;
    }

    private Map<String, Object> generateSankeyData(List<DeadLetterMessage> messages) {
        Map<String, Object> result = new HashMap<>();

        Map<MqTypeEnum, Map<String, Long>> mqTopicCounts = new HashMap<>();
        Map<String, Map<DeadReasonTypeEnum, Long>> topicReasonCounts = new HashMap<>();

        for (DeadLetterMessage msg : messages) {
            MqTypeEnum mqType = msg.getMqType();
            String topic = msg.getTopic();
            DeadReasonTypeEnum reason = msg.getDeadReasonType();

            if (mqType != null && topic != null) {
                mqTopicCounts.computeIfAbsent(mqType, k -> new HashMap<>())
                        .merge(topic, 1L, Long::sum);
            }

            if (topic != null && reason != null) {
                topicReasonCounts.computeIfAbsent(topic, k -> new HashMap<>())
                        .merge(reason, 1L, Long::sum);
            }
        }

        DeadLetterVisualizationService.SankeyData sankey =
                visualizationService.generateSankeyDiagram(mqTopicCounts, topicReasonCounts);

        result.put("success", true);
        result.put("data", sankey);
        return result;
    }

    private Map<String, Object> generateAllVisualizations(List<DeadLetterMessage> messages, String interval) {
        Map<String, Object> result = new HashMap<>();

        Map<LocalDateTime, Long> timeData = messages.stream()
                .collect(Collectors.groupingBy(
                        msg -> msg.getCreateTime() != null ? msg.getCreateTime() : LocalDateTime.now(),
                        Collectors.counting()
                ));

        DeadLetterVisualizationService.TimelineResult timeline =
                visualizationService.generateTimeline(timeData, interval, true, null);

        DeadLetterVisualizationService.HeatmapData heatmap =
                visualizationService.generateHourlyHeatmap(timeData);

        Map<MqTypeEnum, Map<String, Long>> mqTopicCounts = new HashMap<>();
        Map<String, Map<DeadReasonTypeEnum, Long>> topicReasonCounts = new HashMap<>();

        for (DeadLetterMessage msg : messages) {
            MqTypeEnum mqType = msg.getMqType();
            String topic = msg.getTopic();
            DeadReasonTypeEnum reason = msg.getDeadReasonType();

            if (mqType != null && topic != null) {
                mqTopicCounts.computeIfAbsent(mqType, k -> new HashMap<>())
                        .merge(topic, 1L, Long::sum);
            }

            if (topic != null && reason != null) {
                topicReasonCounts.computeIfAbsent(topic, k -> new HashMap<>())
                        .merge(reason, 1L, Long::sum);
            }
        }

        DeadLetterVisualizationService.SankeyData sankey =
                visualizationService.generateSankeyDiagram(mqTopicCounts, topicReasonCounts);

        Map<String, Object> report = visualizationService.generateVisualizationReport(timeline, heatmap, sankey);

        result.put("success", true);
        result.put("data", report);
        return result;
    }

    public Map<String, Object> getRepairCapabilities() {
        return autoRepairService.getRepairCapabilities();
    }

    public Map<String, Object> getVisualizationOptions() {
        return visualizationService.getVisualizationOptions();
    }
}
