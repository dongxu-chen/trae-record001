package com.taskflow.engine;

import com.taskflow.model.WorkflowExecution;
import com.taskflow.repository.WorkflowExecutionRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class QueueConsumer {

    private final TaskQueue taskQueue;
    private final DagExecutor dagExecutor;
    private final WorkflowExecutionRepository workflowExecutionRepository;

    public QueueConsumer(TaskQueue taskQueue,
                         DagExecutor dagExecutor,
                         WorkflowExecutionRepository workflowExecutionRepository) {
        this.taskQueue = taskQueue;
        this.dagExecutor = dagExecutor;
        this.workflowExecutionRepository = workflowExecutionRepository;
    }

    @Scheduled(fixedDelay = 1000)
    public void consume() {
        while (!taskQueue.isEmpty()) {
            try {
                TaskQueue.QueueItem item = taskQueue.dequeue(100);
                if (item != null) {
                    WorkflowExecution execution = workflowExecutionRepository
                            .findById(item.getWorkflowExecutionId())
                            .orElse(null);
                    if (execution != null && "PENDING".equals(execution.getStatus())) {
                        log.info("Consuming workflow execution: {}", execution.getExecutionId());
                        dagExecutor.execute(execution);
                    }
                }
            } catch (Exception e) {
                log.error("Error consuming task from queue", e);
            }
        }
    }
}
