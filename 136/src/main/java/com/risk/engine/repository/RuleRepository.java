package com.risk.engine.repository;

import com.risk.engine.entity.Rule;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface RuleRepository extends JpaRepository<Rule, Long> {

    Optional<Rule> findByRuleCode(String ruleCode);

    List<Rule> findByStatusAndScene(String status, String scene);

    List<Rule> findByStatus(String status);

    @Query("SELECT r FROM Rule r WHERE r.status = 'ENABLED' ORDER BY r.priority DESC")
    List<Rule> findAllEnabledRulesOrderByPriority();
}
