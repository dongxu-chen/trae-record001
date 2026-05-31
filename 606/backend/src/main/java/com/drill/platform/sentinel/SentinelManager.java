package com.drill.platform.sentinel;

import com.alibaba.csp.sentinel.Entry;
import com.alibaba.csp.sentinel.SphU;
import com.alibaba.csp.sentinel.slots.block.BlockException;
import com.alibaba.csp.sentinel.slots.block.degrade.DegradeRule;
import com.alibaba.csp.sentinel.slots.block.degrade.DegradeRuleManager;
import com.alibaba.csp.sentinel.slots.block.flow.FlowRule;
import com.alibaba.csp.sentinel.slots.block.flow.FlowRuleManager;
import com.alibaba.csp.sentinel.slots.system.SystemRule;
import com.alibaba.csp.sentinel.slots.system.SystemRuleManager;
import com.drill.platform.model.RateLimitStrategy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class SentinelManager {

    private final Map<String, RateLimitStrategy> strategyMap = new ConcurrentHashMap<>();
    private final Map<String, SentinelMetric> metricMap = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        log.info("Sentinel Manager initialized");
    }

    public void applyStrategy(RateLimitStrategy strategy) {
        strategyMap.put(strategy.getId(), strategy);
        List<FlowRule> flowRules = new ArrayList<>();
        List<DegradeRule> degradeRules = new ArrayList<>();
        List<SystemRule> systemRules = new ArrayList<>();

        String resource = "drill-resource-" + strategy.getId();

        FlowRule flowRule = new FlowRule();
        flowRule.setResource(resource);
        flowRule.setCount(strategy.getThreshold());

        switch (strategy.getType()) {
            case DIRECT_REJECT:
                flowRule.setControlBehavior(RuleConstant.CONTROL_BEHAVIOR_DEFAULT);
                break;
            case WARM_UP:
                flowRule.setControlBehavior(RuleConstant.CONTROL_BEHAVIOR_WARM_UP);
                flowRule.setWarmUpPeriodSec(strategy.getWarmupPeriodSec());
                break;
            case RATE_LIMITER:
                flowRule.setControlBehavior(RuleConstant.CONTROL_BEHAVIOR_RATE_LIMITER);
                flowRule.setMaxQueueingTimeMs(strategy.getMaxQueueingTimeMs());
                break;
            default:
                flowRule.setControlBehavior(RuleConstant.CONTROL_BEHAVIOR_DEFAULT);
        }

        flowRule.setGrade(RuleConstant.FLOW_GRADE_QPS);
        flowRule.setLimitApp("default");
        flowRules.add(flowRule);

        if (strategy.getCircuitBreakerRatio() > 0) {
            DegradeRule degradeRule = new DegradeRule(resource);
            degradeRule.setCount(strategy.getCircuitBreakerRatio());
            degradeRule.setGrade(RuleConstant.DEGRADE_GRADE_RATIO);
            degradeRule.setTimeWindow(strategy.getCircuitBreakerTimeoutMs() / 1000);
            degradeRule.setMinRequestAmount(5);
            degradeRule.setStatIntervalMs(10000);
            degradeRules.add(degradeRule);
        }

        FlowRuleManager.loadRules(flowRules);
        DegradeRuleManager.loadRules(degradeRules);

        metricMap.put(strategy.getId(), new SentinelMetric());
        log.info("Applied strategy: {} with type: {}, threshold: {}",
                strategy.getName(), strategy.getType(), strategy.getThreshold());
    }

    public SentinelResult entry(String strategyId) {
        String resource = "drill-resource-" + strategyId;
        SentinelMetric metric = metricMap.computeIfAbsent(strategyId, k -> new SentinelMetric());
        Entry entry = null;

        try {
            entry = SphU.entry(resource);
            metric.incrementPassed();
            return SentinelResult.passed(entry);
        } catch (BlockException e) {
            metric.incrementBlocked();
            RateLimitStrategy strategy = strategyMap.get(strategyId);
            String fallback = strategy != null ? strategy.getFallbackResponse() : "Blocked by Sentinel";
            return SentinelResult.blocked(fallback, e.getRule());
        } finally {
            if (entry != null) {
                entry.exit();
            }
        }
    }

    public void recordDegrade(String strategyId) {
        SentinelMetric metric = metricMap.get(strategyId);
        if (metric != null) {
            metric.incrementDegraded();
        }
    }

    public SentinelMetric getMetric(String strategyId) {
        return metricMap.get(strategyId);
    }

    public void removeStrategy(String strategyId) {
        strategyMap.remove(strategyId);
        metricMap.remove(strategyId);
        FlowRuleManager.loadRules(Collections.emptyList());
        DegradeRuleManager.loadRules(Collections.emptyList());
    }

    public void resetMetrics() {
        metricMap.clear();
    }

    public static class RuleConstant {
        public static final int CONTROL_BEHAVIOR_DEFAULT = 0;
        public static final int CONTROL_BEHAVIOR_WARM_UP = 1;
        public static final int CONTROL_BEHAVIOR_RATE_LIMITER = 2;
        public static final int FLOW_GRADE_QPS = 1;
        public static final int DEGRADE_GRADE_RATIO = 1;
    }
}
