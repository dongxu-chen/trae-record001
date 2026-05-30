package com.taskflow.repository;

import com.taskflow.model.Workflow;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface WorkflowRepository extends JpaRepository<Workflow, Long> {
    List<Workflow> findByStatus(String status);
    List<Workflow> findByNameContaining(String name);
}
