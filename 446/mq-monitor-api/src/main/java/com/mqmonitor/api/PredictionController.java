package com.mqmonitor.api;

import com.mqmonitor.common.config.PredictionConfig;
import com.mqmonitor.common.enums.MQType;
import com.mqmonitor.common.model.PredictionResult;
import com.mqmonitor.collector.MetricsManager;
import com.mqmonitor.prediction.PredictionManager;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/prediction")
@CrossOrigin(origins = "*")
public class PredictionController {

    private final PredictionManager predictionManager;
    private final MetricsManager metricsManager;

    public PredictionController() {
        this.metricsManager = MetricsManager.getInstance();
        this.predictionManager = PredictionManager.getInstance(metricsManager.getPredictionConfig());
    }

    @GetMapping("/{mqType}/{cluster}/{topic}")
    public ResponseEntity<PredictionResult> predictBacklog(
            @PathVariable MQType mqType,
            @PathVariable String cluster,
            @PathVariable String topic,
            @RequestParam(required = false) String consumerGroup) {
        PredictionResult result = predictionManager.predictBacklog(mqType, cluster, topic, consumerGroup);
        if (result == null) {
            return ResponseEntity.noContent().build();
        }
        return ResponseEntity.ok(result);
    }

    @GetMapping("/all")
    public ResponseEntity<List<PredictionResult>> predictAll() {
        List<PredictionResult> results = predictionManager.predictAll();
        return ResponseEntity.ok(results);
    }

    @GetMapping("/high-risk")
    public ResponseEntity<List<PredictionResult>> getHighRiskPredictions() {
        List<PredictionResult> highRisk = predictionManager.getHighRiskPredictions();
        return ResponseEntity.ok(highRisk);
    }

    @GetMapping("/config")
    public ResponseEntity<PredictionConfig> getPredictionConfig() {
        return ResponseEntity.ok(predictionManager.getPredictor().getConfig());
    }

    @PutMapping("/config")
    public ResponseEntity<PredictionConfig> updatePredictionConfig(@RequestBody PredictionConfig config) {
        metricsManager.setPredictionConfig(config);
        return ResponseEntity.ok(config);
    }

    @GetMapping("/summary")
    public ResponseEntity<Map<String, Object>> getPredictionSummary() {
        List<PredictionResult> allPredictions = predictionManager.predictAll();
        List<PredictionResult> highRisk = predictionManager.getHighRiskPredictions();

        Map<String, Object> summary = new HashMap<>();
        summary.put("totalPredictions", allPredictions.size());
        summary.put("highRiskCount", highRisk.size());

        long maxPredictedBacklog = 0;
        double avgGrowthRate = 0;
        int willExceedCount = 0;

        for (PredictionResult p : allPredictions) {
            maxPredictedBacklog = Math.max(maxPredictedBacklog, p.getPredictedBacklogAtHorizon());
            avgGrowthRate += p.getGrowthRate();
            if (p.isWillExceedThreshold()) {
                willExceedCount++;
            }
        }

        if (!allPredictions.isEmpty()) {
            avgGrowthRate /= allPredictions.size();
        }

        summary.put("maxPredictedBacklog", maxPredictedBacklog);
        summary.put("averageGrowthRate", Math.round(avgGrowthRate * 100.0) / 100.0);
        summary.put("willExceedThresholdCount", willExceedCount);
        summary.put("predictionHorizonMinutes", predictionManager.getPredictor().getConfig().getPredictionHorizonMinutes());

        return ResponseEntity.ok(summary);
    }
}
