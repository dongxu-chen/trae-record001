package com.taskflow.repository;

import com.taskflow.model.TaskExecution;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface TaskExecutionRepository extends JpaRepository<TaskExecution, Long> {
    List<TaskExecution> findByWorkflowExecutionId(Long workflowExecutionId);
    List<TaskExecution> findByWorkflowExecutionIdAndStatus(Long workflowExecutionId, String status);
    List<TaskExecution> findByTaskId(Long taskId);
}
