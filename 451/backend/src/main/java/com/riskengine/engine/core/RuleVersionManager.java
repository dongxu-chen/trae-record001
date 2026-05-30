package com.riskengine.engine.core;

import com.riskengine.model.RuleDefinition;
import com.riskengine.model.RuleVersion;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

@Slf4j
@Component
public class RuleVersionManager {

    private final Map<Long, List<RuleVersion>> versionHistory = new ConcurrentHashMap<>();
    private final AtomicLong versionIdGenerator = new AtomicLong(1);
    private final int maxVersionHistory = 20;

    public RuleVersion createVersion(RuleDefinition rule, String changeLog, String operator) {
        RuleVersion version = new RuleVersion();
        version.setId(versionIdGenerator.getAndIncrement());
        version.setRuleId(rule.getId());
        version.setRuleCode(rule.getRuleCode());
        version.setVersion(rule.getVersion());
        version.setRuleContent(rule.getRuleContent());
        version.setDroolsDrl(rule.getDroolsDrl());
        version.setGroovyScript(rule.getGroovyScript());
        version.setChangeLog(changeLog);
        version.setOperator(operator);

        versionHistory.computeIfAbsent(rule.getId(), k -> new ArrayList<>()).add(version);

        trimVersionHistory(rule.getId());

        log.info("Rule version created: ruleCode={}, version={}, operator={}",
                rule.getRuleCode(), rule.getVersion(), operator);

        return version;
    }

    private void trimVersionHistory(Long ruleId) {
        List<RuleVersion> versions = versionHistory.get(ruleId);
        if (versions != null && versions.size() > maxVersionHistory) {
            versions.sort(Comparator.comparingInt(RuleVersion::getVersion).reversed());
            while (versions.size() > maxVersionHistory) {
                versions.remove(versions.size() - 1);
            }
        }
    }

    public List<RuleVersion> getVersionHistory(Long ruleId) {
        List<RuleVersion> versions = versionHistory.getOrDefault(ruleId, new ArrayList<>());
        return versions.stream()
                .sorted(Comparator.comparingInt(RuleVersion::getVersion).reversed())
                .collect(Collectors.toList());
    }

    public Optional<RuleVersion> getVersion(Long ruleId, Integer version) {
        return versionHistory.getOrDefault(ruleId, new ArrayList<>()).stream()
                .filter(v -> v.getVersion().equals(version))
                .findFirst();
    }

    public RuleDefinition rollbackToVersion(RuleDefinition currentRule, Integer targetVersion) {
        Optional<RuleVersion> targetOpt = getVersion(currentRule.getId(), targetVersion);
        if (!targetOpt.isPresent()) {
            throw new RuntimeException("Version not found: " + targetVersion);
        }

        RuleVersion target = targetOpt.get();
        currentRule.setRuleContent(target.getRuleContent());
        currentRule.setDroolsDrl(target.getDroolsDrl());
        currentRule.setGroovyScript(target.getGroovyScript());
        currentRule.setVersion(currentRule.getVersion() + 1);
        currentRule.setUpdateTime(java.time.LocalDateTime.now());

        log.info("Rule rolled back: ruleCode={}, from version={} to new version={}",
                currentRule.getRuleCode(), targetVersion, currentRule.getVersion());

        return currentRule;
    }
}
