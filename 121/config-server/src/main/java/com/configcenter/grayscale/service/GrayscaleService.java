package com.configcenter.grayscale.service;

import com.configcenter.grayscale.entity.GrayscaleRule;
import com.configcenter.grayscale.repository.GrayscaleRuleRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.config.environment.Environment;
import org.springframework.cloud.config.server.environment.EnvironmentRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class GrayscaleService {

    private static final Logger logger = LoggerFactory.getLogger(GrayscaleService.class);

    @Autowired
    private GrayscaleRuleRepository ruleRepository;

    @Autowired
    private EnvironmentRepository environmentRepository;

    private final Map<String, Map<String, Object>> grayscaleConfigCache = new ConcurrentHashMap<>();

    public GrayscaleRule createRule(GrayscaleRule rule, String createdBy) {
        String id = "GR-" + System.currentTimeMillis();
        rule.setId(id);
        rule.setCreatedBy(createdBy);
        rule.setCreatedAt(LocalDateTime.now());
        rule.setUpdatedAt(LocalDateTime.now());
        rule.setStatus(GrayscaleRule.GrayscaleStatus.DRAFT);

        ruleRepository.save(id, rule);
        logger.info("Created grayscale rule: {}", id);
        return rule;
    }

    public GrayscaleRule updateRule(String id, GrayscaleRule updatedRule) {
        return ruleRepository.findById(id).map(rule -> {
            if (updatedRule.getTargetIps() != null) {
                rule.setTargetIps(updatedRule.getTargetIps());
            }
            if (updatedRule.getTargetInstances() != null) {
                rule.setTargetInstances(updatedRule.getTargetInstances());
            }
            if (updatedRule.getPercentage() != null) {
                rule.setPercentage(updatedRule.getPercentage());
            }
            if (updatedRule.getDescription() != null) {
                rule.setDescription(updatedRule.getDescription());
            }
            rule.setUpdatedAt(LocalDateTime.now());
            ruleRepository.save(id, rule);
            logger.info("Updated grayscale rule: {}", id);
            return rule;
        }).orElseThrow(() -> new RuntimeException("Rule not found: " + id));
    }

    public GrayscaleRule activateRule(String id) {
        GrayscaleRule rule = ruleRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Rule not found: " + id));

        rule.setStatus(GrayscaleRule.GrayscaleStatus.ACTIVE);
        rule.setUpdatedAt(LocalDateTime.now());
        ruleRepository.save(id, rule);

        cacheGrayscaleConfig(rule);
        logger.info("Activated grayscale rule: {}", id);
        return rule;
    }

    public GrayscaleRule pauseRule(String id) {
        GrayscaleRule rule = ruleRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Rule not found: " + id));

        rule.setStatus(GrayscaleRule.GrayscaleStatus.PAUSED);
        rule.setUpdatedAt(LocalDateTime.now());
        ruleRepository.save(id, rule);

        logger.info("Paused grayscale rule: {}", id);
        return rule;
    }

    public GrayscaleRule completeRule(String id) {
        GrayscaleRule rule = ruleRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Rule not found: " + id));

        rule.setStatus(GrayscaleRule.GrayscaleStatus.COMPLETED);
        rule.setUpdatedAt(LocalDateTime.now());
        ruleRepository.save(id, rule);

        removeGrayscaleConfigCache(rule);
        logger.info("Completed grayscale rule: {}", id);
        return rule;
    }

    public void deleteRule(String id) {
        ruleRepository.deleteById(id);
        logger.info("Deleted grayscale rule: {}", id);
    }

    public Optional<GrayscaleRule> getRule(String id) {
        return ruleRepository.findById(id);
    }

    public List<GrayscaleRule> getAllRules() {
        return ruleRepository.findAll();
    }

    public List<GrayscaleRule> getRulesByService(String serviceName) {
        return ruleRepository.findByServiceName(serviceName);
    }

    public List<GrayscaleRule> getActiveRules() {
        return ruleRepository.findByStatus(GrayscaleRule.GrayscaleStatus.ACTIVE);
    }

    public boolean isTargetForGrayscale(String serviceName, String ip, String instanceId) {
        List<GrayscaleRule> activeRules = ruleRepository.findByServiceNameAndStatus(
                serviceName, GrayscaleRule.GrayscaleStatus.ACTIVE);

        for (GrayscaleRule rule : activeRules) {
            switch (rule.getType()) {
                case IP:
                    if (rule.getTargetIps().contains(ip)) {
                        return true;
                    }
                    break;
                case INSTANCE:
                    if (rule.getTargetInstances().contains(instanceId)) {
                        return true;
                    }
                    break;
                case PERCENTAGE:
                    if (isInPercentage(serviceName, instanceId, rule.getPercentage())) {
                        return true;
                    }
                    break;
            }
        }
        return false;
    }

    private boolean isInPercentage(String serviceName, String instanceId, int percentage) {
        if (instanceId == null) return false;
        int hash = (serviceName + instanceId).hashCode();
        return (hash & Integer.MAX_VALUE) % 100 < percentage;
    }

    public Map<String, Object> getGrayscaleConfig(String serviceName, String profile, String label) {
        String cacheKey = serviceName + ":" + profile + ":" + label;
        return grayscaleConfigCache.get(cacheKey);
    }

    private void cacheGrayscaleConfig(GrayscaleRule rule) {
        String cacheKey = rule.getServiceName() + ":" + rule.getProfile() + ":" + rule.getLabel();
        try {
            Environment env = environmentRepository.findOne(
                    rule.getServiceName(), rule.getProfile(), rule.getLabel(), false);
            Map<String, Object> configMap = new HashMap<>();
            if (env != null && env.getPropertySources() != null) {
                env.getPropertySources().forEach(source -> {
                    if (source.getSource() instanceof Map) {
                        configMap.putAll((Map) source.getSource());
                    }
                });
            }
            grayscaleConfigCache.put(cacheKey, configMap);
        } catch (Exception e) {
            logger.error("Error caching grayscale config: {}", cacheKey, e);
        }
    }

    private void removeGrayscaleConfigCache(GrayscaleRule rule) {
        String cacheKey = rule.getServiceName() + ":" + rule.getProfile() + ":" + rule.getLabel();
        grayscaleConfigCache.remove(cacheKey);
    }

    public Map<String, Object> getGrayscaleStatus() {
        Map<String, Object> status = new HashMap<>();
        long activeCount = getActiveRules().size();
        long draftCount = ruleRepository.findByStatus(GrayscaleRule.GrayscaleStatus.DRAFT).size();
        long pausedCount = ruleRepository.findByStatus(GrayscaleRule.GrayscaleStatus.PAUSED).size();

        status.put("activeRules", activeCount);
        status.put("draftRules", draftCount);
        status.put("pausedRules", pausedCount);
        status.put("cachedConfigs", grayscaleConfigCache.size());
        return status;
    }
}
