package com.taskflow.service;

import com.taskflow.dto.ExecutionDto;
import com.taskflow.engine.TaskQueue;
import com.taskflow.model.TaskExecution;
import com.taskflow.model.Workflow;
import com.taskflow.model.WorkflowExecution;
import com.taskflow.repository.TaskExecutionRepository;
import com.taskflow.repository.WorkflowExecutionRepository;
import com.taskflow.repository.WorkflowRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class ExecutionService {

    private final WorkflowExecutionRepository workflowExecutionRepository;
    private final TaskExecutionRepository taskExecutionRepository;
    private final WorkflowRepository workflowRepository;
    private final TaskQueue taskQueue;

    @Transactional
    public ExecutionDto triggerExecution(Long workflowId, String triggerType) {
        Workflow workflow = workflowRepository.findById(workflowId)
                .orElseThrow(() -> new RuntimeException("Workflow not found: " + workflowId));

        if (!"PUBLISHED".equals(workflow.getStatus())) {
            throw new RuntimeException("Workflow is not published: " + workflowId);
        }

        WorkflowExecution execution = new WorkflowExecution();
        execution.setWorkflowId(workflowId);
        execution.setExecutionId("exec-" + UUID.randomUUID().toString().substring(0, 8));
        execution.setStatus("PENDING");
        execution.setTriggerType(triggerType != null ? triggerType : "MANUAL");
        execution = workflowExecutionRepository.save(execution);

        taskQueue.enqueue(execution.getId(), "WORKFLOW");

        return toDto(execution);
    }

    public ExecutionDto getExecution(String executionId) {
        WorkflowExecution execution = workflowExecutionRepository.findByExecutionId(executionId)
                .orElseThrow(() -> new RuntimeException("Execution not found: " + executionId));
        return toDto(execution);
    }

    public List<ExecutionDto> listExecutions(Long workflowId) {
        List<WorkflowExecution> executions;
        if (workflowId != null) {
            executions = workflowExecutionRepository.findByWorkflowIdOrderByCreatedAtDesc(workflowId);
        } else {
            executions = workflowExecutionRepository.findAll();
        }
        return executions.stream().map(this::toDto).collect(Collectors.toList());
    }

    @Transactional
    public ExecutionDto retryExecution(String executionId) {
        WorkflowExecution execution = workflowExecutionRepository.findByExecutionId(executionId)
                .orElseThrow(() -> new RuntimeException("Execution not found: " + executionId));

        WorkflowExecution newExecution = new WorkflowExecution();
        newExecution.setWorkflowId(execution.getWorkflowId());
        newExecution.setExecutionId("exec-" + UUID.randomUUID().toString().substring(0, 8));
        newExecution.setStatus("PENDING");
        newExecution.setTriggerType("RETRY");
        newExecution = workflowExecutionRepository.save(newExecution);

        taskQueue.enqueue(newExecution.getId(), "WORKFLOW");

        return toDto(newExecution);
    }

    @Transactional
    public void cancelExecution(String executionId) {
        WorkflowExecution execution = workflowExecutionRepository.findByExecutionId(executionId)
                .orElseThrow(() -> new RuntimeException("Execution not found: " + executionId));

        if ("RUNNING".equals(execution.getStatus()) || "PENDING".equals(execution.getStatus())) {
            execution.setStatus("CANCELLED");
            execution.setFinishedAt(LocalDateTime.now());
            workflowExecutionRepository.save(execution);

            List<TaskExecution> taskExecutions = taskExecutionRepository
                    .findByWorkflowExecutionId(execution.getId());
            for (TaskExecution te : taskExecutions) {
                if ("PENDING".equals(te.getStatus()) || "RUNNING".equals(te.getStatus())) {
                    te.setStatus("CANCELLED");
                    te.setFinishedAt(LocalDateTime.now());
                    taskExecutionRepository.save(te);
                }
            }
        }
    }

    private ExecutionDto toDto(WorkflowExecution execution) {
        ExecutionDto dto = new ExecutionDto();
        dto.setId(execution.getId());
        dto.setWorkflowId(execution.getWorkflowId());
        dto.setExecutionId(execution.getExecutionId());
        dto.setStatus(execution.getStatus());
        dto.setTriggerType(execution.getTriggerType());
        dto.setTriggerId(execution.getTriggerId());
        dto.setStartedAt(execution.getStartedAt());
        dto.setFinishedAt(execution.getFinishedAt());

        List<TaskExecution> taskExecutions = taskExecutionRepository
                .findByWorkflowExecutionId(execution.getId());
        dto.setTaskExecutions(taskExecutions.stream().map(this::toTaskExecDto).collect(Collectors.toList()));

        return dto;
    }

    private ExecutionDto.TaskExecutionDto toTaskExecDto(TaskExecution te) {
        ExecutionDto.TaskExecutionDto dto = new ExecutionDto.TaskExecutionDto();
        dto.setId(te.getId());
        dto.setTaskId(te.getTaskId());
        dto.setTaskKey(te.getTaskKey());
        dto.setStatus(te.getStatus());
        dto.setAttempt(te.getAttempt());
        dto.setWorkerNode(te.getWorkerNode());
        dto.setStartedAt(te.getStartedAt());
        dto.setFinishedAt(te.getFinishedAt());
        dto.setDurationMs(te.getDurationMs());
        dto.setLogText(te.getLogText());
        dto.setErrorMessage(te.getErrorMessage());
        return dto;
    }
}
