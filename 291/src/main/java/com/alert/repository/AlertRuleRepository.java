package com.alert.repository;

import com.alert.entity.AlertRule;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface AlertRuleRepository extends JpaRepository<AlertRule, Long> {

    Optional<AlertRule> findByRuleName(String ruleName);

    List<AlertRule> findByEnabledTrue();

    List<AlertRule> findByRuleTypeAndEnabledTrue(String ruleType);
}
