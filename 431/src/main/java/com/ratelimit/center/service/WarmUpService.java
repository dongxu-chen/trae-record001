package com.ratelimit.center.service;

import com.alibaba.csp.sentinel.slots.block.RuleConstant;
import com.alibaba.csp.sentinel.slots.block.flow.FlowRule;
import com.alibaba.csp.sentinel.slots.block.flow.FlowRuleManager;
import com.ratelimit.center.common.RateLimitConstants;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class WarmUpService {

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @Value("${rate-limit.warm-up.enabled:true}")
    private boolean warmUpEnabled;

    @Value("${rate-limit.warm-up.default-warm-up-period-seconds:10}")
    private int defaultWarmUpPeriod;

    private final Map<String, WarmUpState> warmUpStateMap = new ConcurrentHashMap<>();

    @Getter
    public static class WarmUpState {
        private final String resource;
        private final double targetQps;
        private final long startTime;
        private final long warmUpPeriodMs;
        private final int curveType;
        private final double exponentialFactor;
        private volatile boolean completed;

        public WarmUpState(String resource, double targetQps, long warmUpPeriodMs, int curveType, double exponentialFactor) {
            this.resource = resource;
            this.targetQps = targetQps;
            this.startTime = System.currentTimeMillis();
            this.warmUpPeriodMs = warmUpPeriodMs;
            this.curveType = curveType;
            this.exponentialFactor = exponentialFactor;
            this.completed = false;
        }

        public double getCurrentLimit() {
            if (completed) {
                return targetQps;
            }
            long elapsed = System.currentTimeMillis() - startTime;
            if (elapsed >= warmUpPeriodMs) {
                completed = true;
                return targetQps;
            }
            double ratio = (double) elapsed / warmUpPeriodMs;

            switch (curveType) {
                case RateLimitConstants.WARM_UP_CURVE_EXPONENTIAL:
                    return calculateExponential(ratio);
                case RateLimitConstants.WARM_UP_CURVE_LINEAR:
                default:
                    return calculateLinear(ratio);
            }
        }

        private double calculateLinear(double ratio) {
            return targetQps * ratio;
        }

        private double calculateExponential(double ratio) {
            double factor = exponentialFactor > 0 ? exponentialFactor : 3.0;
            double expValue = (Math.pow(factor, ratio) - 1) / (factor - 1);
            return targetQps * expValue;
        }

        public double getCurrentRatio() {
            if (completed) {
                return 1.0;
            }
            long elapsed = System.currentTimeMillis() - startTime;
            return Math.min(1.0, (double) elapsed / warmUpPeriodMs);
        }
    }

    @FunctionalInterface
    public interface WarmUpCurve {
        double calculate(double ratio, double targetQps, double factor);
    }

    public static final Map<Integer, WarmUpCurve> CURVES = new ConcurrentHashMap<>();

    static {
        CURVES.put(RateLimitConstants.WARM_UP_CURVE_LINEAR, (ratio, target, factor) -> target * ratio);

        CURVES.put(RateLimitConstants.WARM_UP_CURVE_EXPONENTIAL, (ratio, target, factor) -> {
            double f = factor > 0 ? factor : 3.0;
            double expValue = (Math.pow(f, ratio) - 1) / (f - 1);
            return target * expValue;
        });
    }

    @PostConstruct
    public void init() {
        if (!warmUpEnabled) {
            log.info("Warm-up feature is disabled");
            return;
        }
        log.info("Warm-up feature initialized, default period: {}s, supported curves: LINEAR, EXPONENTIAL", defaultWarmUpPeriod);
    }

    public void startWarmUp(String resource, double targetQps, int warmUpSeconds) {
        startWarmUp(resource, targetQps, warmUpSeconds, RateLimitConstants.WARM_UP_CURVE_LINEAR, 3.0);
    }

    public void startWarmUp(String resource, double targetQps, int warmUpSeconds, int curveType, Double exponentialFactor) {
        if (!warmUpEnabled) {
            return;
        }

        long warmUpPeriodMs = warmUpSeconds > 0 ? warmUpSeconds * 1000L : defaultWarmUpPeriod * 1000L;
        double factor = (exponentialFactor != null && exponentialFactor > 1.0) ? exponentialFactor : 3.0;

        WarmUpState state = new WarmUpState(resource, targetQps, warmUpPeriodMs, curveType, factor);
        warmUpStateMap.put(resource, state);

        String curveName = curveType == RateLimitConstants.WARM_UP_CURVE_EXPONENTIAL ? "EXPONENTIAL" : "LINEAR";
        log.info("Started warm-up for resource: {}, target QPS: {}, duration: {}s, curve: {}, factor: {}",
                resource, targetQps, warmUpSeconds, curveName, factor);

        updateFlowRuleWithWarmUp(resource, targetQps, warmUpSeconds);
    }

    public void startLinearWarmUp(String resource, double targetQps, int warmUpSeconds) {
        startWarmUp(resource, targetQps, warmUpSeconds, RateLimitConstants.WARM_UP_CURVE_LINEAR, null);
    }

    public void startExponentialWarmUp(String resource, double targetQps, int warmUpSeconds, double factor) {
        startWarmUp(resource, targetQps, warmUpSeconds, RateLimitConstants.WARM_UP_CURVE_EXPONENTIAL, factor);
    }

    private void updateFlowRuleWithWarmUp(String resource, double targetQps, int warmUpSeconds) {
        List<FlowRule> rules = FlowRuleManager.getRules();
        boolean found = false;

        for (FlowRule rule : rules) {
            if (resource.equals(rule.getResource())) {
                rule.setControlBehavior(RuleConstant.CONTROL_BEHAVIOR_WARM_UP);
                rule.setCount(targetQps);
                rule.setWarmUpPeriodSec(warmUpSeconds);
                found = true;
                break;
            }
        }

        if (!found) {
            FlowRule rule = new FlowRule();
            rule.setResource(resource);
            rule.setGrade(RuleConstant.FLOW_GRADE_QPS);
            rule.setCount(targetQps);
            rule.setControlBehavior(RuleConstant.CONTROL_BEHAVIOR_WARM_UP);
            rule.setWarmUpPeriodSec(warmUpSeconds);
            rule.setLimitApp("default");
            rules.add(rule);
        }

        FlowRuleManager.loadRules(rules);
    }

    public double getCurrentWarmUpLimit(String resource) {
        WarmUpState state = warmUpStateMap.get(resource);
        if (state == null) {
            return -1;
        }
        return state.getCurrentLimit();
    }

    public boolean isWarmUpCompleted(String resource) {
        WarmUpState state = warmUpStateMap.get(resource);
        if (state == null) {
            return true;
        }
        return state.completed;
    }

    public Map<String, Object> getWarmUpStatus(String resource) {
        WarmUpState state = warmUpStateMap.get(resource);
        if (state == null) {
            return null;
        }

        Map<String, Object> status = new LinkedHashMap<>();
        status.put("resource", state.resource);
        status.put("targetQps", state.targetQps);
        status.put("currentLimit", state.getCurrentLimit());
        status.put("currentRatio", state.getCurrentRatio());
        status.put("startTime", state.startTime);
        status.put("warmUpPeriodMs", state.warmUpPeriodMs);
        status.put("elapsedMs", System.currentTimeMillis() - state.startTime);
        status.put("completed", state.completed);
        status.put("curveType", state.curveType);
        status.put("curveName", state.curveType == RateLimitConstants.WARM_UP_CURVE_EXPONENTIAL ? "EXPONENTIAL" : "LINEAR");
        status.put("exponentialFactor", state.exponentialFactor);

        return status;
    }

    public List<Map<String, Object>> getAllWarmUpStatus() {
        List<Map<String, Object>> list = new ArrayList<>();
        for (Map.Entry<String, WarmUpState> entry : warmUpStateMap.entrySet()) {
            Map<String, Object> status = getWarmUpStatus(entry.getKey());
            if (status != null) {
                list.add(status);
            }
        }
        return list;
    }

    @Scheduled(fixedRate = 1000)
    public void checkWarmUpCompletion() {
        if (!warmUpEnabled) {
            return;
        }

        warmUpStateMap.forEach((resource, state) -> {
            if (!state.completed && state.getCurrentLimit() >= state.targetQps) {
                state.completed = true;
                log.info("Warm-up completed for resource: {}, target QPS: {}", resource, state.targetQps);
            }
        });
    }

    public void stopWarmUp(String resource) {
        WarmUpState state = warmUpStateMap.remove(resource);
        if (state != null) {
            log.info("Stopped warm-up for resource: {}", resource);

            List<FlowRule> rules = FlowRuleManager.getRules();
            for (FlowRule rule : rules) {
                if (resource.equals(rule.getResource())) {
                    rule.setControlBehavior(RuleConstant.CONTROL_BEHAVIOR_DEFAULT);
                    rule.setWarmUpPeriodSec(0);
                    break;
                }
            }
            FlowRuleManager.loadRules(rules);
        }
    }

    public List<Map<String, Object>> getWarmUpCurveChart(String resource, int points) {
        WarmUpState state = warmUpStateMap.get(resource);
        if (state == null) {
            return Collections.emptyList();
        }

        List<Map<String, Object>> chart = new ArrayList<>();
        int n = Math.max(10, Math.min(points, 100));

        for (int i = 0; i <= n; i++) {
            double ratio = (double) i / n;
            double limit;
            switch (state.curveType) {
                case RateLimitConstants.WARM_UP_CURVE_EXPONENTIAL:
                    limit = CURVES.get(RateLimitConstants.WARM_UP_CURVE_EXPONENTIAL)
                            .calculate(ratio, state.targetQps, state.exponentialFactor);
                    break;
                case RateLimitConstants.WARM_UP_CURVE_LINEAR:
                default:
                    limit = CURVES.get(RateLimitConstants.WARM_UP_CURVE_LINEAR)
                            .calculate(ratio, state.targetQps, state.exponentialFactor);
                    break;
            }

            Map<String, Object> point = new LinkedHashMap<>();
            point.put("ratio", ratio);
            point.put("timeMs", (long) (ratio * state.warmUpPeriodMs));
            point.put("limit", limit);
            chart.add(point);
        }

        return chart;
    }
}
