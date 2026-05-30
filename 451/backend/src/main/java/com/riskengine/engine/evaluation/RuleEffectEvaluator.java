package com.riskengine.engine.evaluation;

import com.riskengine.model.EffectEvaluation;
import com.riskengine.model.RuleDefinition;
import com.riskengine.redis.RedisStatsService;
import com.riskengine.repository.RuleRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Slf4j
@Service
public class RuleEffectEvaluator {

    private final RedisStatsService redisStatsService;
    private final RuleRepository ruleRepository;

    private static final String KEY_RULE_HIT = "risk:stats:rule:hit:";
    private static final String KEY_ACTION = "risk:stats:action:";

    public RuleEffectEvaluator(RedisStatsService redisStatsService, RuleRepository ruleRepository) {
        this.redisStatsService = redisStatsService;
        this.ruleRepository = ruleRepository;
    }

    public List<EffectEvaluation> evaluateRuleEffect(String ruleCode, int beforeHours, int afterHours) {
        List<EffectEvaluation> results = new ArrayList<>();
        Optional<RuleDefinition> ruleOpt = ruleRepository.findByRuleCode(ruleCode);

        if (ruleOpt.isEmpty()) {
            EffectEvaluation ev = new EffectEvaluation();
            ev.setRuleCode(ruleCode);
            ev.setConclusion("规则不存在");
            results.add(ev);
            return results;
        }

        RuleDefinition rule = ruleOpt.get();
        EffectEvaluation evaluation = buildEvaluation(rule, beforeHours, afterHours);
        results.add(evaluation);

        return results;
    }

    public List<EffectEvaluation> evaluateAllRules(int beforeHours, int afterHours) {
        List<RuleDefinition> rules = ruleRepository.findAll();
        List<EffectEvaluation> results = new ArrayList<>();

        for (RuleDefinition rule : rules) {
            try {
                EffectEvaluation ev = buildEvaluation(rule, beforeHours, afterHours);
                results.add(ev);
            } catch (Exception e) {
                log.error("Failed to evaluate rule: {}", rule.getRuleCode(), e);
            }
        }

        results.sort(Comparator.comparingDouble(EffectEvaluation::getHitRateChange).reversed());
        return results;
    }

    private EffectEvaluation buildEvaluation(RuleDefinition rule, int beforeHours, int afterHours) {
        EffectEvaluation ev = new EffectEvaluation();
        ev.setRuleCode(rule.getRuleCode());
        ev.setRuleName(rule.getRuleName());
        ev.setEvaluationId("EVAL_" + System.currentTimeMillis());

        LocalDateTime now = LocalDateTime.now();

        PeriodStats before = collectPeriodStats(rule.getRuleCode(), now.minusHours(beforeHours + afterHours), now.minusHours(afterHours));
        PeriodStats after = collectPeriodStats(rule.getRuleCode(), now.minusHours(afterHours), now);

        ev.setBeforeTotalEvents(before.totalEvents);
        ev.setBeforeHitCount(before.hitCount);
        ev.setBeforeHitRate(before.hitRate);
        ev.setBeforeRejectCount(before.rejectCount);
        ev.setBeforeRejectRate(before.rejectRate);

        ev.setAfterTotalEvents(after.totalEvents);
        ev.setAfterHitCount(after.hitCount);
        ev.setAfterHitRate(after.hitRate);
        ev.setAfterRejectCount(after.rejectCount);
        ev.setAfterRejectRate(after.rejectRate);

        ev.setHitRateChange(ev.getAfterHitRate() - ev.getBeforeHitRate());
        ev.setRejectRateChange(ev.getAfterRejectRate() - ev.getBeforeRejectRate());

        ev.setConclusion(generateConclusion(ev));

        return ev;
    }

    private PeriodStats collectPeriodStats(String ruleCode, LocalDateTime start, LocalDateTime end) {
        PeriodStats stats = new PeriodStats();
        long totalHits = 0;
        long totalEvents = 0;

        LocalDateTime current = start;
        while (current.isBefore(end)) {
            String hourKey = current.format(DateTimeFormatter.ofPattern("yyyy-MM-dd:HH"));
            String hitKey = KEY_RULE_HIT + ruleCode + ":hour:" + hourKey;
            totalHits += redisStatsService.getRawLong(hitKey, 0L);
            current = current.plusHours(1);
        }

        String totalKey = "risk:stats:event:total";
        totalEvents = redisStatsService.getRawLong(totalKey, 0L);

        stats.totalEvents = totalEvents > 0 ? totalEvents : 0;
        stats.hitCount = totalHits;
        stats.hitRate = stats.totalEvents > 0 ? (double) stats.hitCount / stats.totalEvents * 100 : 0.0;

        long rejectCount = redisStatsService.getRawLong(KEY_ACTION + "REJECT", 0L)
                + redisStatsService.getRawLong(KEY_ACTION + "BLOCK", 0L);
        stats.rejectCount = rejectCount;
        stats.rejectRate = stats.totalEvents > 0 ? (double) stats.rejectCount / stats.totalEvents * 100 : 0.0;

        return stats;
    }

    private String generateConclusion(EffectEvaluation ev) {
        double hitChange = ev.getHitRateChange();
        double rejectChange = ev.getRejectRateChange();

        if (Math.abs(hitChange) < 0.5) {
            return "规则上线前后命中率变化不大（<0.5%），效果不明显";
        } else if (hitChange > 0) {
            if (rejectChange > 0) {
                return String.format("规则有效：命中率提升 %.2f%%，拦截率提升 %.2f%%，风控能力增强", hitChange, rejectChange);
            } else {
                return String.format("命中率提升 %.2f%%，但拦截率下降 %.2f%%，需关注误判风险", hitChange, Math.abs(rejectChange));
            }
        } else {
            if (rejectChange < 0) {
                return String.format("命中率下降 %.2f%%，拦截率下降 %.2f%%，规则可能过于宽松", Math.abs(hitChange), Math.abs(rejectChange));
            } else {
                return String.format("命中率下降 %.2f%%，但拦截率上升 %.2f%%，规则更为精准", Math.abs(hitChange), rejectChange);
            }
        }
    }

    private static class PeriodStats {
        long totalEvents;
        long hitCount;
        double hitRate;
        long rejectCount;
        double rejectRate;
    }
}
