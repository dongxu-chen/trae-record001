package com.taskscheduler.core.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.taskscheduler.common.dto.TaskPredictionDTO;
import com.taskscheduler.common.entity.TaskLog;
import com.taskscheduler.core.mapper.TaskLogMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class TaskPredictionService {

    private static final int DEFAULT_SAMPLE_SIZE = 30;
    private static final long CACHE_DURATION_MS = 5 * 60 * 1000;

    @Autowired
    private TaskLogMapper taskLogMapper;

    private final Map<Long, PredictionCache> predictionCache = new ConcurrentHashMap<>();

    private static class PredictionCache {
        TaskPredictionDTO prediction;
        long timestamp;

        PredictionCache(TaskPredictionDTO prediction, long timestamp) {
            this.prediction = prediction;
            this.timestamp = timestamp;
        }
    }

    public TaskPredictionDTO predictTaskDuration(Long taskId) {
        PredictionCache cached = predictionCache.get(taskId);
        long now = System.currentTimeMillis();

        if (cached != null && (now - cached.timestamp) < CACHE_DURATION_MS) {
            log.debug("Return cached prediction for task: {}", taskId);
            return cached.prediction;
        }

        TaskPredictionDTO prediction = calculateTaskPrediction(taskId);
        predictionCache.put(taskId, new PredictionCache(prediction, now));

        return prediction;
    }

    private TaskPredictionDTO calculateTaskPrediction(Long taskId) {
        TaskPredictionDTO dto = new TaskPredictionDTO();
        dto.setTaskId(taskId);

        LocalDateTime startTime = LocalDateTime.now().minusDays(30);

        QueryWrapper<TaskLog> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("task_id", taskId)
                .ge("execute_start_time", startTime)
                .isNotNull("execute_start_time")
                .isNotNull("execute_end_time")
                .orderByDesc("execute_start_time")
                .last("LIMIT " + DEFAULT_SAMPLE_SIZE);

        List<TaskLog> logs = taskLogMapper.selectList(queryWrapper);

        if (logs.isEmpty()) {
            dto.setSampleCount(0L);
            dto.setSuccessCount(0L);
            dto.setFailedCount(0L);
            dto.setPredictedDuration("暂无历史数据");
            return dto;
        }

        List<Double> durations = new ArrayList<>();
        long successCount = 0;
        long failedCount = 0;

        for (TaskLog log : logs) {
            if (log.getExecuteStartTime() != null && log.getExecuteEndTime() != null) {
                long seconds = Duration.between(log.getExecuteStartTime(), log.getExecuteEndTime()).getSeconds();
                durations.add((double) seconds);
            }
            if (log.getExecuteCode() != null && log.getExecuteCode() == 0) {
                successCount++;
            } else {
                failedCount++;
            }
        }

        dto.setSampleCount((long) logs.size());
        dto.setSuccessCount(successCount);
        dto.setFailedCount(failedCount);
        dto.setSuccessRate(logs.size() > 0 ? (double) successCount / logs.size() * 100 : 0.0);

        if (!durations.isEmpty()) {
            Collections.sort(durations);

            double sum = durations.stream().mapToDouble(Double::doubleValue).sum();
            double avg = sum / durations.size();
            dto.setAvgSeconds(avg);
            dto.setMinSeconds(durations.get(0));
            dto.setMaxSeconds(durations.get(durations.size() - 1));
            dto.setMedianSeconds(calculatePercentile(durations, 50));
            dto.setP95Seconds(calculatePercentile(durations, 95));
            dto.setP99Seconds(calculatePercentile(durations, 99));

            double predicted = predictNextDuration(durations, avg);
            dto.setPredictedDuration(formatDuration(predicted));
        } else {
            dto.setPredictedDuration("暂无有效数据");
        }

        return dto;
    }

    private double calculatePercentile(List<Double> sortedData, double percentile) {
        if (sortedData.isEmpty()) {
            return 0.0;
        }

        double index = (percentile / 100.0) * (sortedData.size() - 1);
        int lowerIndex = (int) Math.floor(index);
        int upperIndex = (int) Math.ceil(index);

        if (lowerIndex == upperIndex) {
            return sortedData.get(lowerIndex);
        }

        double lowerValue = sortedData.get(lowerIndex);
        double upperValue = sortedData.get(upperIndex);
        double weight = index - lowerIndex;

        return lowerValue + weight * (upperValue - lowerValue);
    }

    private double predictNextDuration(List<Double> durations, double avg) {
        if (durations.size() <= 3) {
            return avg;
        }

        double weightSum = 0;
        double weightedSum = 0;
        for (int i = 0; i < durations.size(); i++) {
            double weight = 1.0 / (i + 1);
            weightedSum += durations.get(i) * weight;
            weightSum += weight;
        }

        double weightedAvg = weightedSum / weightSum;
        double p95 = calculatePercentile(durations, 95);

        double alpha = 0.7;
        return alpha * weightedAvg + (1 - alpha) * Math.min(p95, avg * 1.5);
    }

    private String formatDuration(double seconds) {
        if (seconds < 60) {
            return String.format("%.1f秒", seconds);
        } else if (seconds < 3600) {
            long minutes = (long) (seconds / 60);
            double remainingSeconds = seconds % 60;
            return String.format("%d分%.1f秒", minutes, remainingSeconds);
        } else {
            long hours = (long) (seconds / 3600);
            long minutes = (long) ((seconds % 3600) / 60);
            return String.format("%d小时%d分钟", hours, minutes);
        }
    }

    public void invalidateCache(Long taskId) {
        predictionCache.remove(taskId);
        log.debug("Prediction cache invalidated for task: {}", taskId);
    }

    public void invalidateAllCache() {
        predictionCache.clear();
        log.debug("All prediction cache invalidated");
    }
}
