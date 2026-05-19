package com.risk.engine.service;

import com.alibaba.fastjson.JSON;
import com.risk.engine.dto.DecisionRequest;
import com.risk.engine.dto.DecisionResponse;
import com.risk.engine.entity.FeatureSnapshot;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
@Service
public class SimulationService {

    @Autowired
    private FeatureSnapshotService snapshotService;

    @Autowired
    private DecisionService decisionService;

    public Map<String, Object> replayByRequestId(String requestId) {
        Map<String, Object> result = new HashMap<>();
        
        Map<String, Object> history = snapshotService.getFeatureHistory(requestId);
        if (history.isEmpty()) {
            result.put("error", "未找到历史请求: " + requestId);
            return result;
        }
        
        result.put("originalRequest", history);
        
        try {
            Object rawData = history.get("rawData");
            if (rawData instanceof Map) {
                DecisionRequest request = new DecisionRequest();
                request.setRequestId(requestId + "_REPLAY_" + System.currentTimeMillis());
                request.setScene((String) history.get("scene"));
                request.setData((Map<String, Object>) rawData);
                
                long startTime = System.currentTimeMillis();
                DecisionResponse response = decisionService.makeDecision(request);
                long duration = System.currentTimeMillis() - startTime;
                
                result.put("replayResponse", response);
                result.put("replayDurationMs", duration);
                
                Map<String, Object> comparison = compareResults(history, response);
                result.put("comparison", comparison);
            }
        } catch (Exception e) {
            log.error("回放请求失败: {}", requestId, e);
            result.put("error", e.getMessage());
        }
        
        return result;
    }

    public Map<String, Object> replayByUserId(String userId, int limit) {
        Map<String, Object> result = new HashMap<>();
        
        List<FeatureSnapshot> snapshots = snapshotService.getUserHistory(userId, limit);
        if (snapshots.isEmpty()) {
            result.put("error", "未找到用户历史记录: " + userId);
            return result;
        }
        
        result.put("totalCount", snapshots.size());
        
        List<Map<String, Object>> replayResults = new ArrayList<>();
        for (FeatureSnapshot snapshot : snapshots) {
            Map<String, Object> replayResult = replayByRequestId(snapshot.getRequestId());
            replayResults.add(replayResult);
        }
        
        result.put("replayResults", replayResults);
        
        Map<String, Integer> stats = new HashMap<>();
        for (Map<String, Object> r : replayResults) {
            Map<String, Object> response = (Map<String, Object>) r.get("replayResponse");
            if (response != null) {
                String decision = (String) response.get("decision");
                stats.put(decision, stats.getOrDefault(decision, 0) + 1);
            }
        }
        result.put("statistics", stats);
        
        return result;
    }

    public Map<String, Object> batchReplay(List<String> requestIds, int concurrency) {
        Map<String, Object> result = new HashMap<>();
        
        ExecutorService executor = Executors.newFixedThreadPool(concurrency);
        CountDownLatch latch = new CountDownLatch(requestIds.size());
        
        AtomicInteger successCount = new AtomicInteger(0);
        AtomicInteger failCount = new AtomicInteger(0);
        List<Future<Map<String, Object>>> futures = new ArrayList<>();
        
        for (String requestId : requestIds) {
            futures.add(executor.submit(() -> {
                try {
                    Map<String, Object> replayResult = replayByRequestId(requestId);
                    if (replayResult.containsKey("error")) {
                        failCount.incrementAndGet();
                    } else {
                        successCount.incrementAndGet();
                    }
                    return replayResult;
                } finally {
                    latch.countDown();
                }
            }));
        }
        
        try {
            latch.await(300, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        
        executor.shutdown();
        
        List<Map<String, Object>> results = new ArrayList<>();
        for (Future<Map<String, Object>> future : futures) {
            try {
                results.add(future.get());
            } catch (Exception e) {
                log.error("获取回放结果失败", e);
            }
        }
        
        result.put("totalCount", requestIds.size());
        result.put("successCount", successCount.get());
        result.put("failCount", failCount.get());
        result.put("results", results);
        
        return result;
    }

    public Map<String, Object> regressionTest(String scene, int sampleSize) {
        Map<String, Object> result = new HashMap<>();
        
        List<FeatureSnapshot> snapshots = snapshotService.getRecentSnapshots(sampleSize);
        List<String> requestIds = new ArrayList<>();
        
        for (FeatureSnapshot snapshot : snapshots) {
            if (scene == null || scene.equals(snapshot.getScene())) {
                requestIds.add(snapshot.getRequestId());
            }
        }
        
        result.put("originalSampleSize", requestIds.size());
        
        if (!requestIds.isEmpty()) {
            Map<String, Object> batchResult = batchReplay(requestIds, 10);
            result.putAll(batchResult);
            
            Map<String, Object> analysis = analyzeRegressionResults((List<Map<String, Object>>) batchResult.get("results"));
            result.put("analysis", analysis);
        }
        
        return result;
    }

    private Map<String, Object> compareResults(Map<String, Object> original, DecisionResponse current) {
        Map<String, Object> comparison = new HashMap<>();
        
        String originalDecision = (String) original.get("decision");
        String currentDecision = current.getDecision();
        
        comparison.put("originalDecision", originalDecision);
        comparison.put("currentDecision", currentDecision);
        comparison.put("decisionChanged", !Objects.equals(originalDecision, currentDecision));
        
        Integer originalScore = (Integer) original.get("score");
        Integer currentScore = current.getScore();
        
        comparison.put("originalScore", originalScore);
        comparison.put("currentScore", currentScore);
        comparison.put("scoreDiff", currentScore != null && originalScore != null ? 
            currentScore - originalScore : null);
        
        return comparison;
    }

    private Map<String, Object> analyzeRegressionResults(List<Map<String, Object>> results) {
        Map<String, Object> analysis = new HashMap<>();
        
        int decisionChanges = 0;
        int scoreIncreased = 0;
        int scoreDecreased = 0;
        
        Map<String, Integer> originalDecisionCounts = new HashMap<>();
        Map<String, Integer> currentDecisionCounts = new HashMap<>();
        
        for (Map<String, Object> result : results) {
            Map<String, Object> comparison = (Map<String, Object>) result.get("comparison");
            if (comparison != null) {
                Boolean changed = (Boolean) comparison.get("decisionChanged");
                if (Boolean.TRUE.equals(changed)) {
                    decisionChanges++;
                }
                
                String originalDecision = (String) comparison.get("originalDecision");
                String currentDecision = (String) comparison.get("currentDecision");
                originalDecisionCounts.put(originalDecision, originalDecisionCounts.getOrDefault(originalDecision, 0) + 1);
                currentDecisionCounts.put(currentDecision, currentDecisionCounts.getOrDefault(currentDecision, 0) + 1);
                
                Integer scoreDiff = (Integer) comparison.get("scoreDiff");
                if (scoreDiff != null) {
                    if (scoreDiff > 0) {
                        scoreIncreased++;
                    } else if (scoreDiff < 0) {
                        scoreDecreased++;
                    }
                }
            }
        }
        
        analysis.put("decisionChangeCount", decisionChanges);
        analysis.put("decisionChangeRate", results.size() > 0 ? (double) decisionChanges / results.size() : 0);
        analysis.put("scoreIncreasedCount", scoreIncreased);
        analysis.put("scoreDecreasedCount", scoreDecreased);
        analysis.put("originalDecisionDistribution", originalDecisionCounts);
        analysis.put("currentDecisionDistribution", currentDecisionCounts);
        
        return analysis;
    }

    public Map<String, Object> customScenarioTest(DecisionRequest baseRequest, 
                                                   List<Map<String, Object>> variations) {
        Map<String, Object> result = new HashMap<>();
        List<Map<String, Object>> testResults = new ArrayList<>();
        
        int index = 0;
        for (Map<String, Object> variation : variations) {
            DecisionRequest testRequest = new DecisionRequest();
            testRequest.setRequestId(baseRequest.getRequestId() + "_TEST_" + (++index));
            testRequest.setScene(baseRequest.getScene());
            
            Map<String, Object> testData = new HashMap<>(baseRequest.getData());
            testData.putAll(variation);
            testRequest.setData(testData);
            
            try {
                DecisionResponse response = decisionService.makeDecision(testRequest);
                Map<String, Object> testResult = new HashMap<>();
                testResult.put("variation", variation);
                testResult.put("response", response);
                testResults.add(testResult);
            } catch (Exception e) {
                Map<String, Object> errorResult = new HashMap<>();
                errorResult.put("variation", variation);
                errorResult.put("error", e.getMessage());
                testResults.add(errorResult);
            }
        }
        
        result.put("testCount", variations.size());
        result.put("testResults", testResults);
        
        return result;
    }
}
