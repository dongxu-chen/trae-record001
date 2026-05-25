package com.alert.repository;

import com.alert.entity.AlertSuppressionRule;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface AlertSuppressionRuleRepository extends JpaRepository<AlertSuppressionRule, Long> {

    Optional<AlertSuppressionRule> findByRuleName(String ruleName);

    List<AlertSuppressionRule> findByEnabledTrue();
}
