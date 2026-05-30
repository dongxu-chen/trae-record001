package com.riskengine.kafka;

import com.alibaba.fastjson.JSON;
import com.riskengine.engine.core.RuleEngineExecutor;
import com.riskengine.model.HitStats;
import com.riskengine.model.RiskDecision;
import com.riskengine.model.RiskEvent;
import com.riskengine.model.RuleDefinition;
import com.riskengine.redis.RedisStatsService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class KafkaEventProcessor {

    private final RuleEngineExecutor ruleEngineExecutor;
    private final KafkaDecisionProducer decisionProducer;
    private final RedisStatsService statsService;

    public KafkaEventProcessor(RuleEngineExecutor ruleEngineExecutor,
                               KafkaDecisionProducer decisionProducer,
                               RedisStatsService statsService) {
        this.ruleEngineExecutor = ruleEngineExecutor;
        this.decisionProducer = decisionProducer;
        this.statsService = statsService;
    }

    public void process(RiskEvent event) {
        long startTime = System.currentTimeMillis();
        log.info("Processing risk event: eventId={}, eventType={}, userId={}",
                event.getEventId(), event.getEventType(), event.getUserId());

        try {
            Map<String, RuleDefinition> activeRules = ruleEngineExecutor.getActiveRules();
            List<RuleDefinition> rules = new ArrayList<>(activeRules.values());

            RiskDecision decision = ruleEngineExecutor.evaluate(event, rules);
            long duration = System.currentTimeMillis() - startTime;

            log.info("Risk decision made: eventId={}, action={}, riskScore={}, hitRules={}, duration={}ms",
                    decision.getEventId(), decision.getAction(), decision.getRiskScore(),
                    decision.getHitRules(), duration);

            decisionProducer.sendDecision(decision);

            statsService.recordHitStats(event, decision);
            statsService.recordDecisionLatency(event.getEventType(), duration);

        } catch (Exception e) {
            log.error("Error processing risk event: eventId={}", event.getEventId(), e);
            statsService.recordError(event.getEventType());
        }
    }
}
