package com.taskflow.repository;

import com.taskflow.model.Task;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface TaskRepository extends JpaRepository<Task, Long> {
    List<Task> findByWorkflowId(Long workflowId);
    void deleteByWorkflowId(Long workflowId);
}
