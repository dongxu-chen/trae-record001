package com.taskflow.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.taskflow.dto.TaskDto;
import com.taskflow.dto.WorkflowDto;
import com.taskflow.model.Task;
import com.taskflow.model.Workflow;
import com.taskflow.repository.TaskRepository;
import com.taskflow.repository.WorkflowRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Collections;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class WorkflowService {

    private final WorkflowRepository workflowRepository;
    private final TaskRepository taskRepository;
    private final ObjectMapper objectMapper;

    @Transactional
    public WorkflowDto createWorkflow(WorkflowDto.CreateRequest request) {
        Workflow workflow = new Workflow();
        workflow.setName(request.getName());
        workflow.setDescription(request.getDescription());
        workflow.setDagJson(request.getDagJson() != null ? request.getDagJson() : "{}");
        workflow.setStatus("DRAFT");
        workflow.setCreatedBy("system");
        workflow = workflowRepository.save(workflow);

        if (request.getTasks() != null) {
            saveTasks(workflow.getId(), request.getTasks());
        }

        return toDto(workflow);
    }

    @Transactional
    public WorkflowDto updateWorkflow(Long id, WorkflowDto.UpdateRequest request) {
        Workflow workflow = workflowRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Workflow not found: " + id));

        if (request.getName() != null) workflow.setName(request.getName());
        if (request.getDescription() != null) workflow.setDescription(request.getDescription());
        if (request.getDagJson() != null) workflow.setDagJson(request.getDagJson());
        workflow.setVersion(workflow.getVersion() + 1);
        workflow = workflowRepository.save(workflow);

        if (request.getTasks() != null) {
            taskRepository.deleteByWorkflowId(id);
            saveTasks(id, request.getTasks());
        }

        return toDto(workflow);
    }

    public WorkflowDto getWorkflow(Long id) {
        Workflow workflow = workflowRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Workflow not found: " + id));
        return toDto(workflow);
    }

    public List<WorkflowDto> listWorkflows() {
        return workflowRepository.findAll().stream()
                .map(this::toDto)
                .collect(Collectors.toList());
    }

    @Transactional
    public void deleteWorkflow(Long id) {
        taskRepository.deleteByWorkflowId(id);
        workflowRepository.deleteById(id);
    }

    @Transactional
    public WorkflowDto publishWorkflow(Long id) {
        Workflow workflow = workflowRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Workflow not found: " + id));
        workflow.setStatus("PUBLISHED");
        workflow = workflowRepository.save(workflow);
        return toDto(workflow);
    }

    private void saveTasks(Long workflowId, List<TaskDto> taskDtos) {
        for (TaskDto dto : taskDtos) {
            Task task = new Task();
            task.setWorkflowId(workflowId);
            task.setTaskKey(dto.getTaskKey() != null ? dto.getTaskKey() : UUID.randomUUID().toString());
            task.setTaskName(dto.getTaskName());
            task.setTaskType(dto.getTaskType() != null ? dto.getTaskType() : "SHELL");
            task.setTaskConfig(dto.getTaskConfig());
            task.setTaskPriority(dto.getTaskPriority() != null ? dto.getTaskPriority() : 5);
            task.setRetryCount(dto.getRetryCount() != null ? dto.getRetryCount() : 0);
            task.setRetryInterval(dto.getRetryInterval() != null ? dto.getRetryInterval() : 30);
            task.setRetryStrategy(dto.getRetryStrategy() != null ? dto.getRetryStrategy() : "FIXED");
            task.setTimeoutSeconds(dto.getTimeoutSeconds() != null ? dto.getTimeoutSeconds() : 3600);
            task.setPositionX(dto.getPositionX() != null ? dto.getPositionX() : 0.0);
            task.setPositionY(dto.getPositionY() != null ? dto.getPositionY() : 0.0);

            try {
                if (dto.getUpstreamKeys() != null && !dto.getUpstreamKeys().isEmpty()) {
                    task.setUpstreamKeys(objectMapper.writeValueAsString(dto.getUpstreamKeys()));
                } else {
                    task.setUpstreamKeys("[]");
                }
            } catch (Exception e) {
                task.setUpstreamKeys("[]");
            }

            try {
                if (dto.getDataProducts() != null && !dto.getDataProducts().isEmpty()) {
                    task.setDataProducts(objectMapper.writeValueAsString(dto.getDataProducts()));
                } else {
                    task.setDataProducts("[]");
                }
            } catch (Exception e) {
                task.setDataProducts("[]");
            }

            taskRepository.save(task);
        }
    }

    private WorkflowDto toDto(Workflow workflow) {
        WorkflowDto dto = new WorkflowDto();
        dto.setId(workflow.getId());
        dto.setName(workflow.getName());
        dto.setDescription(workflow.getDescription());
        dto.setDagJson(workflow.getDagJson());
        dto.setStatus(workflow.getStatus());
        dto.setVersion(workflow.getVersion());
        dto.setCreatedBy(workflow.getCreatedBy());

        List<Task> tasks = taskRepository.findByWorkflowId(workflow.getId());
        dto.setTasks(tasks.stream().map(this::toTaskDto).collect(Collectors.toList()));

        return dto;
    }

    private TaskDto toTaskDto(Task task) {
        TaskDto dto = new TaskDto();
        dto.setId(task.getId());
        dto.setTaskKey(task.getTaskKey());
        dto.setTaskName(task.getTaskName());
        dto.setTaskType(task.getTaskType());
        dto.setTaskConfig(task.getTaskConfig());
        dto.setTaskPriority(task.getTaskPriority());
        dto.setRetryCount(task.getRetryCount());
        dto.setRetryInterval(task.getRetryInterval());
        dto.setRetryStrategy(task.getRetryStrategy());
        dto.setTimeoutSeconds(task.getTimeoutSeconds());
        dto.setPositionX(task.getPositionX());
        dto.setPositionY(task.getPositionY());

        try {
            List<String> keys = objectMapper.readValue(
                    task.getUpstreamKeys() != null ? task.getUpstreamKeys() : "[]",
                    new TypeReference<List<String>>() {});
            dto.setUpstreamKeys(keys);
        } catch (Exception e) {
            dto.setUpstreamKeys(Collections.emptyList());
        }

        try {
            List<String> products = objectMapper.readValue(
                    task.getDataProducts() != null ? task.getDataProducts() : "[]",
                    new TypeReference<List<String>>() {});
            dto.setDataProducts(products);
        } catch (Exception e) {
            dto.setDataProducts(Collections.emptyList());
        }

        return dto;
    }
}
