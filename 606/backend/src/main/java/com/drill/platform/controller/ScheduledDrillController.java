package com.drill.platform.controller;

import com.drill.platform.model.ApiResult;
import com.drill.platform.model.ScheduledDrill;
import com.drill.platform.scheduler.DrillScheduler;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/scheduled")
public class ScheduledDrillController {

    private final DrillScheduler drillScheduler;

    public ScheduledDrillController(DrillScheduler drillScheduler) {
        this.drillScheduler = drillScheduler;
    }

    @GetMapping("/tasks")
    public ApiResult<List<ScheduledDrill>> listScheduledTasks() {
        return ApiResult.success(drillScheduler.listScheduledDrills());
    }

    @GetMapping("/tasks/{taskId}")
    public ApiResult<ScheduledDrill> getScheduledTask(@PathVariable String taskId) {
        ScheduledDrill drill = drillScheduler.getScheduledDrill(taskId);
        if (drill == null) {
            return ApiResult.error(404, "Scheduled task not found");
        }
        return ApiResult.success(drill);
    }

    @PostMapping("/tasks")
    public ApiResult<ScheduledDrill> createScheduledTask(@RequestBody ScheduledDrill drill) {
        ScheduledDrill created = drillScheduler.createScheduledDrill(drill);
        return ApiResult.success(created);
    }

    @PutMapping("/tasks/{taskId}")
    public ApiResult<ScheduledDrill> updateScheduledTask(
            @PathVariable String taskId,
            @RequestBody ScheduledDrill drill) {
        ScheduledDrill updated = drillScheduler.updateScheduledDrill(taskId, drill);
        if (updated == null) {
            return ApiResult.error(404, "Scheduled task not found");
        }
        return ApiResult.success(updated);
    }

    @DeleteMapping("/tasks/{taskId}")
    public ApiResult<Void> deleteScheduledTask(@PathVariable String taskId) {
        boolean deleted = drillScheduler.deleteScheduledDrill(taskId);
        if (!deleted) {
            return ApiResult.error(404, "Scheduled task not found");
        }
        return ApiResult.success(null);
    }

    @PostMapping("/tasks/{taskId}/toggle")
    public ApiResult<ScheduledDrill> toggleScheduledTask(
            @PathVariable String taskId,
            @RequestParam boolean enabled) {
        ScheduledDrill updated = drillScheduler.toggleScheduledDrill(taskId, enabled);
        if (updated == null) {
            return ApiResult.error(404, "Scheduled task not found");
        }
        return ApiResult.success(updated);
    }

    @PostMapping("/tasks/{taskId}/trigger")
    public ApiResult<ScheduledDrill> triggerScheduledTask(@PathVariable String taskId) {
        ScheduledDrill drill = drillScheduler.getScheduledDrill(taskId);
        if (drill == null) {
            return ApiResult.error(404, "Scheduled task not found");
        }
        return ApiResult.success(drill);
    }

    @GetMapping("/stats")
    public ApiResult<Map<String, Object>> getSchedulerStats() {
        return ApiResult.success(drillScheduler.getSchedulerStats());
    }
}
