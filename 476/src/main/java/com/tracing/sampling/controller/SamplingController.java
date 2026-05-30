package com.tracing.sampling.controller;

import com.tracing.sampling.adjuster.AdaptiveRateAdjuster;
import com.tracing.sampling.model.SamplingDecisionRecord;
import com.tracing.sampling.model.SamplingDecisionTree;
import com.tracing.sampling.model.SamplingStats;
import com.tracing.sampling.predictor.TrafficPredictor;
import com.tracing.sampling.predictor.TrafficPredictor.PredictionResult;
import com.tracing.sampling.sampler.IntelligentAdaptiveSampler;
import com.tracing.sampling.store.RedisSamplingConfigStore;
import com.tracing.sampling.store.SamplingConfigStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/sampling")
public class SamplingController {

    private static final Logger logger = LoggerFactory.getLogger(SamplingController.class);

    private final IntelligentAdaptiveSampler sampler;
    private final AdaptiveRateAdjuster rateAdjuster;
    private final SamplingConfigStore configStore;
    private final RedisSamplingConfigStore redisConfigStore;
    private final TrafficPredictor trafficPredictor;

    public SamplingController(IntelligentAdaptiveSampler sampler,
                              AdaptiveRateAdjuster rateAdjuster,
                              SamplingConfigStore configStore,
                              RedisSamplingConfigStore redisConfigStore,
                              TrafficPredictor trafficPredictor) {
        this.sampler = sampler;
        this.rateAdjuster = rateAdjuster;
        this.configStore = configStore;
        this.redisConfigStore = redisConfigStore;
        this.trafficPredictor = trafficPredictor;
    }

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getStats() {
        Map<String, Object> result = new HashMap<>();
        SamplingStats stats = sampler.getStats();
        result.put("stats", stats);
        result.put("errorRateMultiplier", rateAdjuster.getErrorRateMultiplier());
        result.put("errorRateBoostedCount", sampler.getErrorRateBoostedCount());
        result.put("currentErrorRate", trafficPredictor.getCurrentErrorRate());
        result.put("currentRps", trafficPredictor.getCurrentRps());
        return ResponseEntity.ok(result);
    }

    @GetMapping("/rate")
    public ResponseEntity<Map<String, Object>> getCurrentRate() {
        Map<String, Object> result = new HashMap<>();
        result.put("currentSampleRate", sampler.getCurrentSampleRate());
        result.put("movingAverageSPS", rateAdjuster.getMovingAverageSpansPerSecond());
        result.put("errorRateMultiplier", rateAdjuster.getErrorRateMultiplier());
        result.put("description", sampler.getDescription());
        return ResponseEntity.ok(result);
    }

    @PostMapping("/rate")
    public ResponseEntity<Map<String, Object>> setSampleRate(@RequestParam double rate) {
        if (rate < 0.0 || rate > 1.0) {
            return ResponseEntity.badRequest().body(Map.of("error", "Rate must be between 0 and 1"));
        }
        
        sampler.updateSampleRate(rate);
        logger.info("Sample rate manually set to: {}", rate);
        
        return ResponseEntity.ok(Map.of(
                "status", "success",
                "newRate", sampler.getCurrentSampleRate()
        ));
    }

    @PostMapping("/rate/adjust")
    public ResponseEntity<Map<String, Object>> triggerAdjustment() {
        rateAdjuster.triggerAdjustment();
        
        return ResponseEntity.ok(Map.of(
                "status", "success",
                "currentRate", sampler.getCurrentSampleRate(),
                "movingAverageSPS", rateAdjuster.getMovingAverageSpansPerSecond()
        ));
    }

    @GetMapping("/endpoint/{endpointKey}")
    public ResponseEntity<Map<String, Object>> getEndpointConfig(@PathVariable String endpointKey) {
        Map<String, Object> result = new HashMap<>();
        result.put("endpointKey", endpointKey);
        result.put("sampleRateMultiplier", configStore.getEndpointSampleRateMultiplier(endpointKey));
        result.put("averageLatencyMs", configStore.getAverageLatency(endpointKey));
        result.put("latencyStats", redisConfigStore.getLatencyStatsMap(endpointKey));
        
        return ResponseEntity.ok(result);
    }

    @PostMapping("/endpoint/{endpointKey}/multiplier")
    public ResponseEntity<Map<String, Object>> setEndpointMultiplier(
            @PathVariable String endpointKey,
            @RequestParam double multiplier) {
        
        if (multiplier < 0.0 || multiplier > 10.0) {
            return ResponseEntity.badRequest().body(Map.of("error", "Multiplier must be between 0 and 10"));
        }
        
        configStore.setEndpointSampleRateMultiplier(endpointKey, multiplier);
        logger.info("Endpoint multiplier set for {}: {}", endpointKey, multiplier);
        
        return ResponseEntity.ok(Map.of(
                "status", "success",
                "endpointKey", endpointKey,
                "newMultiplier", multiplier
        ));
    }

    @GetMapping("/global")
    public ResponseEntity<Map<String, Object>> getGlobalConfig() {
        Map<String, Object> result = new HashMap<>();
        result.put("currentSampleRate", configStore.getCurrentSampleRate());
        result.put("targetSampleRate", configStore.getGlobalTargetSampleRate());
        
        return ResponseEntity.ok(result);
    }

    @PostMapping("/global/target-rate")
    public ResponseEntity<Map<String, Object>> setGlobalTargetRate(@RequestParam double rate) {
        if (rate < 0.0 || rate > 1.0) {
            return ResponseEntity.badRequest().body(Map.of("error", "Rate must be between 0 and 1"));
        }
        
        configStore.setGlobalTargetSampleRate(rate);
        
        return ResponseEntity.ok(Map.of(
                "status", "success",
                "targetRate", rate
        ));
    }

    @PostMapping("/stats/reset")
    public ResponseEntity<Map<String, Object>> resetStats() {
        sampler.resetStats();
        
        return ResponseEntity.ok(Map.of("status", "success", "message", "Stats reset"));
    }

    @PostMapping("/cache/clear")
    public ResponseEntity<Map<String, Object>> clearCache() {
        redisConfigStore.clearCache();
        
        return ResponseEntity.ok(Map.of("status", "success", "message", "Cache cleared"));
    }

    @GetMapping("/prediction")
    public ResponseEntity<Map<String, Object>> getPrediction() {
        Map<String, Object> result = new HashMap<>();
        
        PredictionResult prediction = trafficPredictor.predictTraffic(60);
        PredictionResult lastPrediction = rateAdjuster.getLastPrediction();
        
        result.put("currentPrediction", prediction);
        result.put("lastAdjustmentPrediction", lastPrediction);
        result.put("currentRps", trafficPredictor.getCurrentRps());
        result.put("currentErrorRate", trafficPredictor.getCurrentErrorRate());
        result.put("dataPointCount", trafficPredictor.getDataPointCount());
        
        return ResponseEntity.ok(result);
    }

    @GetMapping("/decision/{traceId}")
    public ResponseEntity<SamplingDecisionTree> getDecisionTree(@PathVariable String traceId) {
        SamplingDecisionTree tree = sampler.getDecisionTree(traceId);
        if (tree == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(tree);
    }

    @GetMapping("/decisions/recent")
    public ResponseEntity<List<SamplingDecisionRecord>> getRecentDecisions(
            @RequestParam(defaultValue = "20") int limit) {
        List<SamplingDecisionRecord> decisions = sampler.getRecentDecisions();
        if (limit > 0 && limit < decisions.size()) {
            decisions = decisions.subList(decisions.size() - limit, decisions.size());
        }
        return ResponseEntity.ok(decisions);
    }

    @GetMapping("/decision-tree/static")
    public ResponseEntity<Map<String, Object>> getStaticDecisionTree() {
        Map<String, Object> result = new HashMap<>();
        
        DecisionTreeNode root = new DecisionTreeNode("root", "采样决策", "根节点");
        
        DecisionTreeNode parentCheck = new DecisionTreeNode("parent_check", 
                "父链路是否已采样?", 
                "检查父Span的采样状态");
        parentCheck.addChild(buildTreeNode("yes", "父链路已采样", 
                "RECORD_AND_SAMPLE", "PARENT_SAMPLED", true));
        parentCheck.addChild(buildTreeNode("no", "父链路未采样", 
                "继续判断", null, false));
        
        DecisionTreeNode errorCheck = new DecisionTreeNode("error_check",
                "是否为错误请求?", 
                "检查HTTP状态码或error标记");
        errorCheck.addChild(buildTreeNode("yes", "错误请求", 
                "RECORD_AND_SAMPLE", "ERROR_REQUEST", true));
        errorCheck.addChild(buildTreeNode("no", "正常请求", 
                "继续判断", null, false));
        
        DecisionTreeNode latencyCheck = new DecisionTreeNode("latency_check",
                "预测延迟 >= 阈值?", 
                "基于历史数据预测延迟");
        latencyCheck.addChild(buildTreeNode("yes", "高延迟请求", 
                "RECORD_AND_SAMPLE", "HIGH_LATENCY", true));
        latencyCheck.addChild(buildTreeNode("no", "正常延迟", 
                "继续判断", null, false));
        
        DecisionTreeNode rateCalculation = new DecisionTreeNode("rate_calculation",
                "计算最终采样率", 
                "baseRate × importance × endpoint × errorRate");
        
        DecisionTreeNode probabilisticCheck = new DecisionTreeNode("probabilistic_check",
                "随机概率 < 采样率?", 
                "概率采样判断");
        probabilisticCheck.addChild(buildTreeNode("yes", "概率命中", 
                "RECORD_AND_SAMPLE", "PROBABILISTIC", true));
        probabilisticCheck.addChild(buildTreeNode("no", "概率未命中", 
                "DROP", "NOT_SAMPLED", false));
        
        root.addChild(parentCheck);
        parentCheck.getChildren().get(1).addChild(errorCheck);
        errorCheck.getChildren().get(1).addChild(latencyCheck);
        latencyCheck.getChildren().get(1).addChild(rateCalculation);
        rateCalculation.addChild(probabilisticCheck);
        
        result.put("tree", root);
        result.put("factors", Map.of(
                "baseSampleRate", sampler.getCurrentSampleRate(),
                "serviceImportance", sampler.getDescription(),
                "errorRateMultiplier", rateAdjuster.getErrorRateMultiplier(),
                "highLatencyThresholdMs", 500
        ));
        
        return ResponseEntity.ok(result);
    }

    @GetMapping("/error-rate")
    public ResponseEntity<Map<String, Object>> getErrorRateInfo() {
        Map<String, Object> result = new HashMap<>();
        result.put("currentErrorRate", trafficPredictor.getCurrentErrorRate());
        result.put("errorRateMultiplier", rateAdjuster.getErrorRateMultiplier());
        result.put("errorRateThreshold", 0.05);
        result.put("maxMultiplier", 2.0);
        result.put("errorBoostedCount", sampler.getErrorRateBoostedCount());
        return ResponseEntity.ok(result);
    }

    @GetMapping("/cross-service/stats")
    public ResponseEntity<Map<String, Object>> getCrossServiceStats() {
        return ResponseEntity.ok(sampler.getCrossServiceSamplingStats());
    }

    @GetMapping("/feedback/stats")
    public ResponseEntity<Map<String, Object>> getFeedbackStats() {
        return ResponseEntity.ok(sampler.getFeedbackLoopStats());
    }

    @GetMapping("/feedback/estimated")
    public ResponseEntity<Map<String, Object>> getEstimatedMetrics() {
        Map<String, Object> result = new HashMap<>();
        result.put("aggregated", sampler.getAggregatedEstimatedMetrics().toMap());
        result.put("endpoints", sampler.getAllEstimatedMetrics().entrySet().stream()
                .collect(HashMap::new, (m, e) -> m.put(e.getKey(), e.getValue().toMap()), HashMap::putAll));
        return ResponseEntity.ok(result);
    }

    @GetMapping("/cost/analysis")
    public ResponseEntity<Map<String, Object>> getCostAnalysis() {
        return ResponseEntity.ok(sampler.getCostAnalysisSummary());
    }

    @GetMapping("/cost/endpoints")
    public ResponseEntity<Map<String, Object>> getEndpointCostMetrics() {
        Map<String, Object> result = new HashMap<>();
        result.put("endpoints", sampler.getAllEndpointCostMetrics().entrySet().stream()
                .collect(HashMap::new, (m, e) -> m.put(e.getKey(), e.getValue().toMap()), HashMap::putAll));
        return ResponseEntity.ok(result);
    }

    @GetMapping("/cost/recommendation")
    public ResponseEntity<Map<String, Object>> getCostRecommendation() {
        return ResponseEntity.ok(sampler.getCostOptimizationRecommendation().toMap());
    }

    @PostMapping("/stats/reset-all")
    public ResponseEntity<Map<String, Object>> resetAllStats() {
        sampler.resetAllStats();
        logger.info("All statistics reset");
        return ResponseEntity.ok(Map.of("status", "success", "message", "All statistics reset"));
    }

    private DecisionTreeNode buildTreeNode(String id, String condition, String description, 
                                        String decision, boolean result) {
        DecisionTreeNode node = new DecisionTreeNode(id, condition, description);
        node.setResult(result);
        node.setDecision(decision);
        return node;
    }

    public static class DecisionTreeNode {
        private String nodeId;
        private String condition;
        private String description;
        private boolean result;
        private String decision;
        private java.util.List<DecisionTreeNode> children;

        public DecisionTreeNode() {
            this.children = new java.util.ArrayList<>();
        }

        public DecisionTreeNode(String nodeId, String condition, String description) {
            this.nodeId = nodeId;
            this.condition = condition;
            this.description = description;
            this.children = new java.util.ArrayList<>();
        }

        public String getNodeId() {
            return nodeId;
        }

        public void setNodeId(String nodeId) {
            this.nodeId = nodeId;
        }

        public String getCondition() {
            return condition;
        }

        public void setCondition(String condition) {
            this.condition = condition;
        }

        public String getDescription() {
            return description;
        }

        public void setDescription(String description) {
            this.description = description;
        }

        public boolean isResult() {
            return result;
        }

        public void setResult(boolean result) {
            this.result = result;
        }

        public String getDecision() {
            return decision;
        }

        public void setDecision(String decision) {
            this.decision = decision;
        }

        public java.util.List<DecisionTreeNode> getChildren() {
            return children;
        }

        public void setChildren(java.util.List<DecisionTreeNode> children) {
            this.children = children;
        }

        public void addChild(DecisionTreeNode child) {
            this.children.add(child);
        }
    }
}
