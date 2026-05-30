package com.riskengine.service;

import com.riskengine.model.HitStats;
import com.riskengine.redis.RedisStatsService;
import com.riskengine.repository.RuleRepository;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class StatsService {

    private final RedisStatsService redisStatsService;
    private final RuleRepository ruleRepository;

    public StatsService(RedisStatsService redisStatsService, RuleRepository ruleRepository) {
        this.redisStatsService = redisStatsService;
        this.ruleRepository = ruleRepository;
    }

    public List<HitStats> getHitStats() {
        List<String> ruleCodes = ruleRepository.findAll().stream()
                .map(r -> r.getRuleCode())
                .collect(Collectors.toList());
        return redisStatsService.getHitStats(ruleCodes);
    }

    public Map<String, Long> getActionCounts() {
        return redisStatsService.getActionCounts();
    }

    public Map<String, Object> getDashboardStats() {
        return redisStatsService.getDashboardStats();
    }

    public Map<String, Object> getHitStatsByGranularity(String granularity) {
        return redisStatsService.getHitStatsByGranularity(granularity);
    }

    public Map<String, Long> getActionCountsByGranularity(String granularity) {
        return redisStatsService.getActionCountsByGranularity(granularity);
    }

    public Map<String, Object> getTimeSeriesData(String granularity, List<String> ruleCodes) {
        return redisStatsService.getTimeSeriesData(granularity, ruleCodes);
    }
}
