package com.taskflow.controller;

import com.taskflow.dto.ApiResponse;
import com.taskflow.dto.ExecutionDto;
import com.taskflow.service.ExecutionService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/executions")
@RequiredArgsConstructor
public class ExecutionController {

    private final ExecutionService executionService;

    @PostMapping("/trigger/{workflowId}")
    public ApiResponse<ExecutionDto> trigger(@PathVariable Long workflowId,
                                              @RequestParam(defaultValue = "MANUAL") String triggerType) {
        return ApiResponse.success(executionService.triggerExecution(workflowId, triggerType));
    }

    @GetMapping("/{executionId}")
    public ApiResponse<ExecutionDto> get(@PathVariable String executionId) {
        return ApiResponse.success(executionService.getExecution(executionId));
    }

    @GetMapping
    public ApiResponse<List<ExecutionDto>> list(@RequestParam(required = false) Long workflowId) {
        return ApiResponse.success(executionService.listExecutions(workflowId));
    }

    @PostMapping("/{executionId}/retry")
    public ApiResponse<ExecutionDto> retry(@PathVariable String executionId) {
        return ApiResponse.success(executionService.retryExecution(executionId));
    }

    @PostMapping("/{executionId}/cancel")
    public ApiResponse<Void> cancel(@PathVariable String executionId) {
        executionService.cancelExecution(executionId);
        return ApiResponse.success(null);
    }
}
