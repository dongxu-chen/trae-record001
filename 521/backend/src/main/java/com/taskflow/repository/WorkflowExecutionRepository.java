package com.taskflow.repository;

import com.taskflow.model.WorkflowExecution;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface WorkflowExecutionRepository extends JpaRepository<WorkflowExecution, Long> {
    Optional<WorkflowExecution> findByExecutionId(String executionId);
    List<WorkflowExecution> findByWorkflowIdOrderByCreatedAtDesc(Long workflowId);
    List<WorkflowExecution> findByStatus(String status);
    List<WorkflowExecution> findByWorkflowIdAndStatus(Long workflowId, String status);
}
