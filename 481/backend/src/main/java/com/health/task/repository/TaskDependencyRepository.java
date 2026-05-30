package com.health.task.repository;

import com.health.task.entity.TaskDependency;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface TaskDependencyRepository extends JpaRepository<TaskDependency, Long> {

    List<TaskDependency> findByTaskName(String taskName);

    List<TaskDependency> findByUpstreamTaskName(String upstreamTaskName);
}
