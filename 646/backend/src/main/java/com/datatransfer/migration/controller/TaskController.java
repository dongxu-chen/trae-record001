package com.datatransfer.migration.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.datatransfer.migration.engine.MigrationPreValidator;
import com.datatransfer.migration.model.Checkpoint;
import com.datatransfer.migration.model.Task;
import com.datatransfer.migration.model.TaskLog;
import com.datatransfer.migration.service.TaskService;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/tasks")
public class TaskController {
    private final TaskService taskService;

    public TaskController(TaskService taskService) {
        this.taskService = taskService;
    }

    @GetMapping
    public Map<String, Object> list(@RequestParam(defaultValue = "1") int page,
                                    @RequestParam(defaultValue = "10") int size,
                                    @RequestParam(required = false) String status) {
        Page<Task> result = taskService.list(page, size, status);
        Map<String, Object> response = new HashMap<>();
        response.put("list", result.getRecords());
        response.put("total", result.getTotal());
        response.put("page", page);
        response.put("size", size);
        return response;
    }

    @GetMapping("/{id}")
    public Task getById(@PathVariable Long id) {
        return taskService.getById(id);
    }

    @PostMapping
    public Task create(@RequestBody Task task) {
        return taskService.create(task);
    }

    @PutMapping("/{id}")
    public Task update(@PathVariable Long id, @RequestBody Task task) {
        return taskService.update(id, task);
    }

    @DeleteMapping("/{id}")
    public Map<String, Object> delete(@PathVariable Long id) {
        boolean success = taskService.delete(id);
        Map<String, Object> response = new HashMap<>();
        response.put("success", success);
        return response;
    }

    @PostMapping("/{id}/prevalidate")
    public MigrationPreValidator.ValidationResult preValidate(@PathVariable Long id) {
        return taskService.preValidate(id);
    }

    @PostMapping("/{id}/start")
    public Map<String, Object> start(@PathVariable Long id) {
        return taskService.start(id);
    }

    @PostMapping("/{id}/pause")
    public Map<String, Object> pause(@PathVariable Long id) {
        return taskService.pause(id);
    }

    @PostMapping("/{id}/rollback")
    public Map<String, Object> rollback(@PathVariable Long id) {
        return taskService.rollback(id);
    }

    @GetMapping("/{id}/rollback/status")
    public Map<String, Object> getRollbackStatus(@PathVariable Long id) {
        return taskService.getRollbackStatus(id);
    }

    @GetMapping("/{id}/status")
    public Map<String, Object> getStatus(@PathVariable Long id) {
        return taskService.getStatus(id);
    }

    @GetMapping("/{id}/position")
    public Map<String, Object> getRealtimePosition(@PathVariable Long id) {
        return taskService.getRealtimePosition(id);
    }

    @GetMapping("/{id}/checkpoints")
    public List<Checkpoint> getCheckpointHistory(@PathVariable Long id,
                                                  @RequestParam(defaultValue = "20") int limit) {
        return taskService.getCheckpointHistory(id, limit);
    }

    @GetMapping("/{id}/logs")
    public List<TaskLog> getLogs(@PathVariable Long id,
                                 @RequestParam(defaultValue = "100") int limit) {
        return taskService.getLogs(id, limit);
    }

    @GetMapping("/dashboard/stats")
    public Map<String, Object> getDashboardStats() {
        return taskService.getDashboardStats();
    }
}
