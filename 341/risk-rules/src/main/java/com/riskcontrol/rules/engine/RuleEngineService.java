package com.riskcontrol.rules.engine;

import com.riskcontrol.common.model.RiskAssessmentResult;
import com.riskcontrol.common.model.RiskEvent;
import com.riskcontrol.common.model.RuleHit;
import org.kie.api.runtime.KieSession;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class RuleEngineService {

    private static final Logger logger = LoggerFactory.getLogger(RuleEngineService.class);

    private final KieSession kieSession;

    @Autowired
    public RuleEngineService(KieSession kieSession) {
        this.kieSession = kieSession;
    }

    public RiskAssessmentResult evaluateRules(RiskEvent event) {
        long startTime = System.currentTimeMillis();

        RiskAssessmentResult result = RiskAssessmentResult.builder()
                .eventId(event.getEventId())
                .userId(event.getUserId())
                .hitRules(new ArrayList<>())
                .assessmentTimestamp(System.currentTimeMillis())
                .build();

        try {
            List<RuleHit> hitRules = new ArrayList<>();

            kieSession.insert(event);
            kieSession.insert(result);
            kieSession.insert(hitRules);

            int firedRules = kieSession.fireAllRules();

            result.setHitRules(hitRules);
            int ruleScore = result.calculateTotalRuleScore();
            result.setRuleScore(ruleScore);
            event.setRuleScore(ruleScore);

            logger.info("Rule engine fired {} rules for event {}, rule score: {}",
                    firedRules, event.getEventId(), ruleScore);

        } catch (Exception e) {
            logger.error("Error evaluating rules for event: {}", event.getEventId(), e);
            result.setDecisionReason("Rule engine error: " + e.getMessage());
        } finally {
            kieSession.dispose();
        }

        long processingTime = System.currentTimeMillis() - startTime;
        result.setProcessingTimeMs(processingTime);

        return result;
    }
}
