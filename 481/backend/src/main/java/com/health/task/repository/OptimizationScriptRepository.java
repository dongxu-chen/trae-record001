package com.health.task.repository;

import com.health.task.entity.OptimizationScript;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface OptimizationScriptRepository extends JpaRepository<OptimizationScript, Long> {

    List<OptimizationScript> findByIssueCategory(String issueCategory);
}
