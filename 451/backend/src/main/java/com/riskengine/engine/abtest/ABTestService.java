package com.riskengine.engine.abtest;

import com.riskengine.engine.core.RuleEngineExecutor;
import com.riskengine.model.ABTestExperiment;
import com.riskengine.model.RiskDecision;
import com.riskengine.model.RiskEvent;
import com.riskengine.model.RuleDefinition;
import com.riskengine.redis.RedisStatsService;
import com.riskengine.repository.RuleRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Service
public class ABTestService {

    private final Map<Long, ABTestExperiment> experiments = new ConcurrentHashMap<>();
    private final AtomicLong idGenerator = new AtomicLong(1);
    private final RuleRepository ruleRepository;
    private final RuleEngineExecutor ruleEngineExecutor;
    private final RedisStatsService redisStatsService;

    public ABTestService(RuleRepository ruleRepository,
                         RuleEngineExecutor ruleEngineExecutor,
                         RedisStatsService redisStatsService) {
        this.ruleRepository = ruleRepository;
        this.ruleEngineExecutor = ruleEngineExecutor;
        this.redisStatsService = redisStatsService;
    }

    public ABTestExperiment createExperiment(ABTestExperiment experiment) {
        experiment.setId(idGenerator.getAndIncrement());
        experiment.setStatus("RUNNING");
        experiment.setCreateTime(LocalDateTime.now());
        experiment.setUpdateTime(LocalDateTime.now());
        experiments.put(experiment.getId(), experiment);

        log.info("A/B Test experiment created: code={}, traffic={}%",
                experiment.getExperimentCode(), experiment.getTrafficPercentage());
        return experiment;
    }

    public ABTestExperiment getExperiment(Long id) {
        return experiments.get(id);
    }

    public List<ABTestExperiment> getAllExperiments() {
        return new ArrayList<>(experiments.values());
    }

    public void stopExperiment(Long id) {
        ABTestExperiment exp = experiments.get(id);
        if (exp != null) {
            exp.setStatus("STOPPED");
            exp.setEndTime(LocalDateTime.now());
            exp.setUpdateTime(LocalDateTime.now());
            log.info("A/B Test experiment stopped: code={}", exp.getExperimentCode());
        }
    }

    public void startExperiment(Long id) {
        ABTestExperiment exp = experiments.get(id);
        if (exp != null) {
            exp.setStatus("RUNNING");
            exp.setStartTime(LocalDateTime.now());
            exp.setUpdateTime(LocalDateTime.now());
            log.info("A/B Test experiment started: code={}", exp.getExperimentCode());
        }
    }

    public void deleteExperiment(Long id) {
        ABTestExperiment removed = experiments.remove(id);
        if (removed != null) {
            log.info("A/B Test experiment deleted: code={}", removed.getExperimentCode());
        }
    }

    public boolean isExperimentTraffic(ABTestExperiment experiment, RiskEvent event) {
        if (!"RUNNING".equals(experiment.getStatus())) {
            return false;
        }
        return shouldRouteToExperiment(experiment, event);
    }

    public RiskDecision evaluateWithABTest(RiskEvent event) {
        List<ABTestExperiment> runningExperiments = experiments.values().stream()
                .filter(e -> "RUNNING".equals(e.getStatus()))
                .toList();

        for (ABTestExperiment experiment : runningExperiments) {
            if (shouldRouteToExperiment(experiment, event)) {
                log.info("Event {} routed to A/B test experiment: {}",
                        event.getEventId(), experiment.getExperimentCode());

                List<RuleDefinition> experimentRules = ruleRepository.findAll().stream()
                        .filter(r -> experiment.getExperimentRuleCodes().contains(r.getRuleCode()))
                        .toList();

                RiskDecision decision = ruleEngineExecutor.evaluate(event, experimentRules);

                String statsKey = "abtest:" + experiment.getExperimentCode() + ":experiment";
                redisStatsService.incrByRaw(statsKey + ":total", 1);
                if (!decision.getHitRules().isEmpty()) {
                    redisStatsService.incrByRaw(statsKey + ":hit", 1);
                }
                redisStatsService.incrByRaw(statsKey + ":score:" + decision.getAction().toLowerCase(), 1);

                decision.getRiskTags().add("AB_TEST:" + experiment.getExperimentCode());
                return decision;
            }
        }

        Map<String, RuleDefinition> activeRules = ruleEngineExecutor.getActiveRules();
        return ruleEngineExecutor.evaluate(event, new ArrayList<>(activeRules.values()));
    }

    private boolean shouldRouteToExperiment(ABTestExperiment experiment, RiskEvent event) {
        int trafficPercentage = experiment.getTrafficPercentage();
        if (trafficPercentage <= 0) return false;
        if (trafficPercentage >= 100) return true;

        String splitKey;
        switch (experiment.getSplitStrategy()) {
            case "USER_ID_HASH":
                splitKey = event.getUserId() != null ? event.getUserId() : event.getEventId();
                break;
            case "IP_HASH":
                splitKey = event.getIp() != null ? event.getIp() : event.getEventId();
                break;
            case "RANDOM":
                splitKey = String.valueOf(Math.random());
                break;
            default:
                splitKey = event.getUserId() != null ? event.getUserId() : event.getEventId();
        }

        int hash = hashKey(splitKey);
        return Math.abs(hash % 100) < trafficPercentage;
    }

    private int hashKey(String key) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] digest = md.digest(key.getBytes(StandardCharsets.UTF_8));
            return Math.abs(digest[0]) | (Math.abs(digest[1]) << 8);
        } catch (Exception e) {
            return key.hashCode();
        }
    }

    public Map<String, Object> getExperimentStats(Long experimentId) {
        ABTestExperiment exp = experiments.get(experimentId);
        if (exp == null) return Collections.emptyMap();

        String baseKey = "abtest:" + exp.getExperimentCode();
        Map<String, Object> stats = new HashMap<>();

        Map<String, Object> baselineStats = new HashMap<>();
        baselineStats.put("total", redisStatsService.getRawLong(baseKey + ":baseline:total", 0L));
        baselineStats.put("hit", redisStatsService.getRawLong(baseKey + ":baseline:hit", 0L));
        baselineStats.put("pass", redisStatsService.getRawLong(baseKey + ":baseline:score:pass", 0L));
        baselineStats.put("review", redisStatsService.getRawLong(baseKey + ":baseline:score:review", 0L));
        baselineStats.put("reject", redisStatsService.getRawLong(baseKey + ":baseline:score:reject", 0L));
        baselineStats.put("block", redisStatsService.getRawLong(baseKey + ":baseline:score:block", 0L));

        Map<String, Object> experimentStats = new HashMap<>();
        experimentStats.put("total", redisStatsService.getRawLong(baseKey + ":experiment:total", 0L));
        experimentStats.put("hit", redisStatsService.getRawLong(baseKey + ":experiment:hit", 0L));
        experimentStats.put("pass", redisStatsService.getRawLong(baseKey + ":experiment:score:pass", 0L));
        experimentStats.put("review", redisStatsService.getRawLong(baseKey + ":experiment:score:review", 0L));
        experimentStats.put("reject", redisStatsService.getRawLong(baseKey + ":experiment:score:reject", 0L));
        experimentStats.put("block", redisStatsService.getRawLong(baseKey + ":experiment:score:block", 0L));

        Long bTotal = (Long) baselineStats.getOrDefault("total", 0L);
        Long bHit = (Long) baselineStats.getOrDefault("hit", 0L);
        Long eTotal = (Long) experimentStats.getOrDefault("total", 0L);
        Long eHit = (Long) experimentStats.getOrDefault("hit", 0L);

        baselineStats.put("hitRate", bTotal > 0 ? (double) bHit / bTotal * 100 : 0.0);
        experimentStats.put("hitRate", eTotal > 0 ? (double) eHit / eTotal * 100 : 0.0);

        stats.put("experiment", exp);
        stats.put("baseline", baselineStats);
        stats.put("experimentGroup", experimentStats);

        if (bTotal > 0 && eTotal > 0) {
            double bRate = (double) bHit / bTotal;
            double eRate = (double) eHit / eTotal;
            stats.put("hitRateDiff", (eRate - bRate) * 100);
            stats.put("conclusion", eRate > bRate ? "实验组拦截率更高" :
                    eRate < bRate ? "基线组拦截率更高" : "两组拦截率相当");
        }

        return stats;
    }
}
