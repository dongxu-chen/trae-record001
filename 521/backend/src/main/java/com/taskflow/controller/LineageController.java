package com.taskflow.controller;

import com.taskflow.dto.ApiResponse;
import com.taskflow.model.TaskLineage;
import com.taskflow.service.LineageService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/lineage")
@RequiredArgsConstructor
public class LineageController {

    private final LineageService lineageService;

    @PostMapping
    public ApiResponse<TaskLineage> create(@RequestBody Map<String, Object> request) {
        String dataProduct = (String) request.get("dataProduct");
        Long targetWorkflowId = Long.valueOf(request.get("targetWorkflowId").toString());
        TaskLineage lineage = lineageService.createLineage(dataProduct, targetWorkflowId);
        return ApiResponse.success(lineage);
    }

    @GetMapping("/source/{workflowId}")
    public ApiResponse<List<TaskLineage>> listBySource(@PathVariable Long workflowId) {
        return ApiResponse.success(lineageService.listBySource(workflowId));
    }

    @GetMapping("/target/{workflowId}")
    public ApiResponse<List<TaskLineage>> listByTarget(@PathVariable Long workflowId) {
        return ApiResponse.success(lineageService.listByTarget(workflowId));
    }

    @PostMapping("/{id}/toggle")
    public ApiResponse<Void> toggle(@PathVariable Long id, @RequestParam boolean enabled) {
        lineageService.toggleLineage(id, enabled);
        return ApiResponse.success(null);
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable Long id) {
        lineageService.deleteLineage(id);
        return ApiResponse.success(null);
    }
}
