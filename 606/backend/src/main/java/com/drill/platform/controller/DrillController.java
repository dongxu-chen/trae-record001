package com.drill.platform.controller;

import com.drill.platform.model.*;
import com.drill.platform.service.DrillService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/drill")
public class DrillController {

    private final DrillService drillService;

    public DrillController(DrillService drillService) {
        this.drillService = drillService;
    }

    @PostMapping("/tasks")
    public ApiResult<DrillTask> createTask(@RequestBody DrillTask task) {
        return ApiResult.success(drillService.createTask(task));
    }

    @PostMapping("/tasks/{taskId}/start")
    public ApiResult<DrillTask> startTask(
            @PathVariable String taskId,
            @RequestParam(defaultValue = "simulator") String mode) {
        return ApiResult.success(drillService.startTask(taskId, mode));
    }

    @PostMapping("/tasks/{taskId}/stop")
    public ApiResult<DrillTask> stopTask(@PathVariable String taskId) {
        return ApiResult.success(drillService.stopTask(taskId));
    }

    @GetMapping("/tasks")
    public ApiResult<List<DrillTask>> listTasks() {
        return ApiResult.success(drillService.listTasks());
    }

    @GetMapping("/tasks/{taskId}")
    public ApiResult<DrillTask> getTask(@PathVariable String taskId) {
        DrillTask task = drillService.getTask(taskId);
        if (task == null) {
            return ApiResult.error(404, "Task not found");
        }
        return ApiResult.success(task);
    }

    @DeleteMapping("/tasks/{taskId}")
    public ApiResult<Void> deleteTask(@PathVariable String taskId) {
        drillService.deleteTask(taskId);
        return ApiResult.success(null);
    }
}
