package com.ratelimit.center.controller;

import com.ratelimit.center.common.Result;
import com.ratelimit.center.sandbox.RuleSandboxService;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/sandbox")
public class SandboxController {

    @Autowired
    private RuleSandboxService ruleSandboxService;

    @PostMapping("/start")
    public Result<Map<String, String>> startSandbox(@RequestBody RuleSandboxService.SandboxRequest request) {
        String taskId = ruleSandboxService.startSandbox(request);
        return Result.success(Map.of("taskId", taskId));
    }

    @GetMapping("/result/{taskId}")
    public Result<RuleSandboxService.SandboxResult> getSandboxResult(@PathVariable String taskId) {
        RuleSandboxService.SandboxResult result = ruleSandboxService.getSandboxResult(taskId);
        if (result == null) {
            return Result.fail(404, "Task not found");
        }
        return Result.success(result);
    }

    @PostMapping("/stop/{taskId}")
    public Result<Void> stopSandbox(@PathVariable String taskId) {
        ruleSandboxService.stopSandbox(taskId);
        return Result.success();
    }

    @GetMapping("/tasks")
    public Result<List<RuleSandboxService.SandboxResult>> listTasks() {
        return Result.success(ruleSandboxService.listSandboxTasks());
    }

    @PostMapping("/quick-test")
    public Result<RuleSandboxService.SandboxResult> quickTest(@RequestBody QuickTestRequest request) {
        return Result.success(ruleSandboxService.quickTest(
                request.getFlowRule(), request.getTestQps(), request.getDurationSeconds()));
    }

    @Data
    public static class QuickTestRequest {
        private com.ratelimit.center.entity.FlowRuleEntity flowRule;
        private int testQps = 200;
        private int durationSeconds = 10;
    }
}
