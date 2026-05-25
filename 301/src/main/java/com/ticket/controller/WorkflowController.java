package com.ticket.controller;

import com.ticket.common.Result;
import com.ticket.workflow.TicketWorkflowService;
import lombok.RequiredArgsConstructor;
import org.flowable.task.api.Task;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/workflow")
@RequiredArgsConstructor
public class WorkflowController {

    private final TicketWorkflowService workflowService;

    @GetMapping("/task/{processInstanceId}")
    public Result<Task> getCurrentTask(@PathVariable String processInstanceId) {
        Task task = workflowService.getCurrentTask(processInstanceId);
        return Result.success(task);
    }

    @PostMapping("/task/{processInstanceId}/complete")
    public Result<Void> completeTask(
            @PathVariable String processInstanceId,
            @RequestParam(required = false) Long userId,
            @RequestBody(required = false) Map<String, Object> variables) {
        workflowService.completeTask(processInstanceId, userId, variables);
        return Result.success();
    }

    @PostMapping("/task/{taskId}/claim")
    public Result<Void> claimTask(@PathVariable String taskId, @RequestParam Long userId) {
        workflowService.claimTask(taskId, userId);
        return Result.success();
    }

    @PostMapping("/task/{taskId}/transfer")
    public Result<Void> transferTask(
            @PathVariable String taskId,
            @RequestParam Long fromUserId,
            @RequestParam Long toUserId) {
        workflowService.transferTask(taskId, fromUserId, toUserId);
        return Result.success();
    }

    @PostMapping("/process/{processInstanceId}/suspend")
    public Result<Void> suspendProcess(@PathVariable String processInstanceId) {
        workflowService.suspendProcess(processInstanceId);
        return Result.success();
    }

    @PostMapping("/process/{processInstanceId}/activate")
    public Result<Void> activateProcess(@PathVariable String processInstanceId) {
        workflowService.activateProcess(processInstanceId);
        return Result.success();
    }

    @DeleteMapping("/process/{processInstanceId}")
    public Result<Void> deleteProcess(
            @PathVariable String processInstanceId,
            @RequestParam(defaultValue = "手动删除") String reason) {
        workflowService.deleteProcess(processInstanceId, reason);
        return Result.success();
    }

    @PostMapping("/process/{processInstanceId}/variable")
    public Result<Void> setVariable(
            @PathVariable String processInstanceId,
            @RequestParam String key,
            @RequestParam Object value) {
        workflowService.setVariable(processInstanceId, key, value);
        return Result.success();
    }

    @GetMapping("/process/{processInstanceId}/variable")
    public Result<Object> getVariable(
            @PathVariable String processInstanceId,
            @RequestParam String key) {
        Object value = workflowService.getVariable(processInstanceId, key);
        return Result.success(value);
    }
}
