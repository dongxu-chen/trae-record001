package com.mqmonitor.prediction;

import com.mqmonitor.common.config.PredictionConfig;
import com.mqmonitor.common.enums.MQType;
import com.mqmonitor.common.model.PredictionResult;
import com.mqmonitor.common.model.QueueMetrics;
import com.mqmonitor.collector.MetricsManager;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

public class PredictionManager {
    private static PredictionManager instance;
    private final TimeSeriesPredictor predictor;
    private final MetricsManager metricsManager;
    private final ConcurrentHashMap<String, PredictionResult> predictionCache = new ConcurrentHashMap<>();

    private PredictionManager(PredictionConfig config) {
        this.metricsManager = MetricsManager.getInstance();
        this.predictor = new TimeSeriesPredictor(config);
    }

    public static synchronized PredictionManager getInstance(PredictionConfig config) {
        if (instance == null) {
            instance = new PredictionManager(config);
        }
        return instance;
    }

    public PredictionResult predictBacklog(MQType mqType, String clusterName, String topic, String consumerGroup) {
        String key = mqType + ":" + clusterName + ":" + topic + (consumerGroup != null ? ":" + consumerGroup : "");
        PredictionResult result = predictor.predictBacklog(mqType, clusterName, topic, consumerGroup);
        if (result != null) {
            predictionCache.put(key, result);
        }
        return result;
    }

    public List<PredictionResult> predictAll() {
        List<PredictionResult> results = new ArrayList<>();
        List<QueueMetrics> allMetrics = metricsManager.getAllMetrics();

        for (QueueMetrics metrics : allMetrics) {
            PredictionResult result = predictBacklog(
                    metrics.getMqType(),
                    metrics.getClusterName(),
                    metrics.getTopic(),
                    metrics.getConsumerGroup()
            );
            if (result != null) {
                results.add(result);
            }
        }
        return results;
    }

    public List<PredictionResult> getHighRiskPredictions() {
        List<PredictionResult> highRisk = new ArrayList<>();
        for (PredictionResult result : predictionCache.values()) {
            if (result.isWillExceedThreshold()) {
                highRisk.add(result);
            }
        }
        return highRisk;
    }

    public PredictionResult getCachedPrediction(MQType mqType, String clusterName, String topic, String consumerGroup) {
        String key = mqType + ":" + clusterName + ":" + topic + (consumerGroup != null ? ":" + consumerGroup : "");
        return predictionCache.get(key);
    }

    public TimeSeriesPredictor getPredictor() {
        return predictor;
    }
}
