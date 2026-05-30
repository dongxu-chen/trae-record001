package com.health.task.repository;

import com.health.task.entity.TaskWeightConfig;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface TaskWeightConfigRepository extends JpaRepository<TaskWeightConfig, Long> {

    Optional<TaskWeightConfig> findByTaskName(String taskName);
}
