package com.riskengine.repository;

import com.riskengine.model.RuleDefinition;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

@Repository
public class RuleRepository {

    private final Map<Long, RuleDefinition> store = new ConcurrentHashMap<>();
    private final AtomicLong idGenerator = new AtomicLong(1);

    public RuleDefinition save(RuleDefinition rule) {
        if (rule.getId() == null) {
            rule.setId(idGenerator.getAndIncrement());
            rule.setCreateTime(LocalDateTime.now());
        }
        rule.setUpdateTime(LocalDateTime.now());
        store.put(rule.getId(), rule);
        return rule;
    }

    public Optional<RuleDefinition> findById(Long id) {
        return Optional.ofNullable(store.get(id));
    }

    public Optional<RuleDefinition> findByRuleCode(String ruleCode) {
        return store.values().stream()
                .filter(r -> r.getRuleCode().equals(ruleCode))
                .findFirst();
    }

    public List<RuleDefinition> findAll() {
        return new ArrayList<>(store.values());
    }

    public List<RuleDefinition> findByEnabled(Boolean enabled) {
        return store.values().stream()
                .filter(r -> r.getEnabled().equals(enabled))
                .collect(Collectors.toList());
    }

    public List<RuleDefinition> findBySceneCode(String sceneCode) {
        return store.values().stream()
                .filter(r -> sceneCode.equals(r.getSceneCode()))
                .collect(Collectors.toList());
    }

    public void deleteById(Long id) {
        store.remove(id);
    }

    public List<RuleDefinition> findByRuleType(String ruleType) {
        return store.values().stream()
                .filter(r -> ruleType.equals(r.getRuleType()))
                .collect(Collectors.toList());
    }
}
