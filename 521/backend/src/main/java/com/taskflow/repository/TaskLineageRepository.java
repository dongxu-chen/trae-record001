package com.taskflow.repository;

import com.taskflow.model.TaskLineage;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface TaskLineageRepository extends JpaRepository<TaskLineage, Long> {
    List<TaskLineage> findByDataProductAndEnabledTrue(String dataProduct);
    List<TaskLineage> findByTargetWorkflowId(Long targetWorkflowId);
    List<TaskLineage> findBySourceWorkflowId(Long sourceWorkflowId);
}
