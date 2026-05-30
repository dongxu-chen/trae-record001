package com.taskflow.controller;

import com.taskflow.dto.ApiResponse;
import com.taskflow.dto.WorkflowDto;
import com.taskflow.service.WorkflowService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/workflows")
@RequiredArgsConstructor
public class WorkflowController {

    private final WorkflowService workflowService;

    @PostMapping
    public ApiResponse<WorkflowDto> create(@RequestBody WorkflowDto.CreateRequest request) {
        return ApiResponse.success(workflowService.createWorkflow(request));
    }

    @PutMapping("/{id}")
    public ApiResponse<WorkflowDto> update(@PathVariable Long id,
                                            @RequestBody WorkflowDto.UpdateRequest request) {
        return ApiResponse.success(workflowService.updateWorkflow(id, request));
    }

    @GetMapping("/{id}")
    public ApiResponse<WorkflowDto> get(@PathVariable Long id) {
        return ApiResponse.success(workflowService.getWorkflow(id));
    }

    @GetMapping
    public ApiResponse<List<WorkflowDto>> list() {
        return ApiResponse.success(workflowService.listWorkflows());
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable Long id) {
        workflowService.deleteWorkflow(id);
        return ApiResponse.success(null);
    }

    @PostMapping("/{id}/publish")
    public ApiResponse<WorkflowDto> publish(@PathVariable Long id) {
        return ApiResponse.success(workflowService.publishWorkflow(id));
    }
}
