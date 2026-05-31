package com.distributed.lock.analysis;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/lock-analysis")
public class LockAnalysisController {

    private final LockAnalysisService analysisService;
    private final LockRecommendationService recommendationService;
    private final LockWaitPredictor waitPredictor;
    private final LockTimeoutAdvisor timeoutAdvisor;

    @Autowired
    public LockAnalysisController(LockAnalysisService analysisService,
                                  LockRecommendationService recommendationService,
                                  LockWaitPredictor waitPredictor,
                                  LockTimeoutAdvisor timeoutAdvisor) {
        this.analysisService = analysisService;
        this.recommendationService = recommendationService;
        this.waitPredictor = waitPredictor;
        this.timeoutAdvisor = timeoutAdvisor;
    }

    @GetMapping("/hot-locks")
    public List<LockAnalysisService.LockStatistics> getHotLocks(@RequestParam(defaultValue = "10") int topN) {
        return analysisService.getHotLocks(topN);
    }

    @GetMapping("/high-contention-locks")
    public List<LockAnalysisService.LockStatistics> getHighContentionLocks(@RequestParam(defaultValue = "10") int topN) {
        return analysisService.getHighContentionLocks(topN);
    }

    @GetMapping("/statistics/{lockKey}")
    public Map<String, Object> getLockStatistics(@PathVariable String lockKey) {
        return analysisService.getLockStatistics(lockKey);
    }

    @GetMapping("/deadlocks")
    public List<LockAnalysisService.DeadlockInfo> detectPotentialDeadlocks() {
        return analysisService.detectPotentialDeadlocks();
    }

    @GetMapping("/overview")
    public Map<String, Object> getOverallStatistics() {
        return analysisService.getOverallStatistics();
    }

    @GetMapping("/dynamic-window-info")
    public Map<String, Object> getDynamicWindowInfo() {
        return analysisService.getDynamicWindowInfo();
    }

    @GetMapping("/recommendations")
    public List<LockRecommendationService.LockRecommendation> getLockRecommendations() {
        return recommendationService.analyzeLockGranularity();
    }

    @GetMapping("/recommendations/{lockKey}")
    public LockRecommendationService.LockRecommendation getLockRecommendation(@PathVariable String lockKey) {
        return recommendationService.getRecommendation(lockKey);
    }

    @GetMapping("/wait-prediction/{lockKey}")
    public LockWaitPredictor.WaitPrediction predictWaitTime(@PathVariable String lockKey) {
        return waitPredictor.predictWaitTime(lockKey);
    }

    @GetMapping("/wait-predictions")
    public Map<String, LockWaitPredictor.WaitPrediction> predictAllWaitTimes() {
        return waitPredictor.predictAllLocks();
    }

    @GetMapping("/timeout-advice/{lockKey}")
    public LockTimeoutAdvisor.TimeoutAdvice getTimeoutAdvice(@PathVariable String lockKey) {
        return timeoutAdvisor.getTimeoutAdvice(lockKey);
    }

    @GetMapping("/timeout-advice")
    public Map<String, LockTimeoutAdvisor.TimeoutAdvice> getAllTimeoutAdvice() {
        return timeoutAdvisor.getAllTimeoutAdvice();
    }

    @GetMapping("/timeout-adjustments")
    public List<LockTimeoutAdvisor.TimeoutAdjustmentLog> getTimeoutAdjustments() {
        return timeoutAdvisor.getRecentAdjustments();
    }

    @PostMapping("/timeout-apply/{lockKey}")
    public Map<String, Object> applyRecommendedTimeout(@PathVariable String lockKey) {
        timeoutAdvisor.applyRecommendedTimeout(lockKey);
        LockTimeoutAdvisor.TimeoutConfig config = timeoutAdvisor.getCurrentTimeout(lockKey);
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("lockKey", lockKey);
        result.put("waitTimeoutMs", config.getWaitTimeoutMs());
        result.put("leaseTimeoutMs", config.getLeaseTimeoutMs());
        result.put("status", "applied");
        return result;
    }

    @PostMapping("/timeout-apply/{lockKey}/custom")
    public Map<String, Object> applyCustomTimeout(@PathVariable String lockKey,
                                                   @RequestParam long waitTimeoutMs,
                                                   @RequestParam long leaseTimeoutMs) {
        timeoutAdvisor.applyTimeout(lockKey, waitTimeoutMs, leaseTimeoutMs);
        LockTimeoutAdvisor.TimeoutConfig config = timeoutAdvisor.getCurrentTimeout(lockKey);
        Map<String, Object> result = new java.util.HashMap<>();
        result.put("lockKey", lockKey);
        result.put("waitTimeoutMs", config.getWaitTimeoutMs());
        result.put("leaseTimeoutMs", config.getLeaseTimeoutMs());
        result.put("status", "applied");
        return result;
    }

    @GetMapping("/current-timeouts")
    public Map<String, LockTimeoutAdvisor.TimeoutConfig> getCurrentTimeouts() {
        return timeoutAdvisor.getAllCurrentTimeouts();
    }
}