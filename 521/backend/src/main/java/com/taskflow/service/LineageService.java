package com.taskflow.service;

import com.taskflow.model.TaskLineage;
import com.taskflow.model.Workflow;
import com.taskflow.repository.TaskLineageRepository;
import com.taskflow.repository.WorkflowRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class LineageService {

    private final TaskLineageRepository lineageRepository;
    private final WorkflowRepository workflowRepository;
    private final ExecutionService executionService;

    @Async
    @Transactional
    public void triggerDownstreamByDataProducts(List<String> dataProducts) {
        for (String product : dataProducts) {
            List<TaskLineage> lineages = lineageRepository.findByDataProductAndEnabledTrue(product);
            for (TaskLineage lineage : lineages) {
                try {
                    Workflow wf = workflowRepository.findById(lineage.getTargetWorkflowId()).orElse(null);
                    if (wf == null) {
                        log.warn("Target workflow not found for lineage {}", lineage.getId());
                        continue;
                    }
                    if (!"PUBLISHED".equals(wf.getStatus())) {
                        log.warn("Target workflow {} is not published, skip trigger", wf.getId());
                        continue;
                    }

                    executionService.triggerExecution(wf.getId(), "LINEAGE");
                    log.info("Data lineage triggered: product={}, targetWorkflow={}", product, wf.getId());
                } catch (Exception e) {
                    log.error("Failed to trigger lineage workflow for product {}", product, e);
                }
            }
        }
    }

    public TaskLineage createLineage(String dataProduct, Long targetWorkflowId) {
        TaskLineage lineage = new TaskLineage();
        lineage.setDataProduct(dataProduct);
        lineage.setTargetWorkflowId(targetWorkflowId);
        lineage.setEnabled(true);
        return lineageRepository.save(lineage);
    }

    public List<TaskLineage> listBySource(Long sourceWorkflowId) {
        return lineageRepository.findBySourceWorkflowId(sourceWorkflowId);
    }

    public List<TaskLineage> listByTarget(Long targetWorkflowId) {
        return lineageRepository.findByTargetWorkflowId(targetWorkflowId);
    }

    public void toggleLineage(Long id, boolean enabled) {
        TaskLineage lineage = lineageRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Lineage not found: " + id));
        lineage.setEnabled(enabled);
        lineageRepository.save(lineage);
    }

    public void deleteLineage(Long id) {
        lineageRepository.deleteById(id);
    }
}
