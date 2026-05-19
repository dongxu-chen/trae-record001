package com.risk.engine.repository;

import com.risk.engine.entity.EasyRule;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface EasyRuleRepository extends JpaRepository<EasyRule, Long> {

    Optional<EasyRule> findByRuleCode(String ruleCode);

    List<EasyRule> findBySceneAndStatus(String scene, String status);

    List<EasyRule> findByStatus(String status);

    @Query("SELECT DISTINCT r.scene FROM EasyRule r WHERE r.status = 'ENABLED'")
    List<String> findAllEnabledScenes();
}
