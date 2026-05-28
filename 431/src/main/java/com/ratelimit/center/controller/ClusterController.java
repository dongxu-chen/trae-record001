package com.ratelimit.center.controller;

import com.ratelimit.center.common.Result;
import com.ratelimit.center.service.ClusterFlowService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.Set;

@RestController
@RequestMapping("/api/cluster")
public class ClusterController {

    @Autowired
    private ClusterFlowService clusterFlowService;

    @GetMapping("/state")
    public Result<Map<String, Object>> getClusterState() {
        return Result.success(clusterFlowService.getClusterState());
    }

    @GetMapping("/dc/quotas")
    public Result<Map<String, ClusterFlowService.DcQuota>> getAllDcQuotas() {
        return Result.success(clusterFlowService.getAllDcQuotas());
    }

    @GetMapping("/dc/current")
    public Result<ClusterFlowService.DcQuota> getCurrentDcQuota() {
        return Result.success(clusterFlowService.getCurrentDcQuota());
    }

    @PostMapping("/quota/acquire")
    public Result<Integer> acquireQuota(
            @RequestParam String resource,
            @RequestParam(defaultValue = "1") int tokens) {
        int granted = clusterFlowService.requestLocalQuota(resource, tokens);
        return Result.success(granted);
    }

    @PostMapping("/quota/try")
    public Result<Boolean> tryAcquireQuota(
            @RequestParam String resource,
            @RequestParam(defaultValue = "1") int tokens) {
        return Result.success(clusterFlowService.tryAcquire(resource, tokens));
    }

    @PostMapping("/quota/release")
    public Result<Void> releaseQuota(
            @RequestParam String resource,
            @RequestParam(defaultValue = "1") int tokens) {
        clusterFlowService.releaseQuota(resource, tokens);
        return Result.success();
    }

    @GetMapping("/clients")
    public Result<Set<String>> getClusterClients() {
        return Result.success(clusterFlowService.getClusterClients());
    }

    @GetMapping("/server")
    public Result<String> getClusterServer() {
        return Result.success(clusterFlowService.getClusterServer());
    }

    @PostMapping("/mode/client")
    public Result<Void> switchToClientMode(
            @RequestParam String serverHost,
            @RequestParam(defaultValue = "18730") int serverPort) {
        clusterFlowService.switchToClientMode(serverHost, serverPort);
        return Result.success();
    }

    @PostMapping("/mode/server")
    public Result<Void> switchToServerMode() {
        clusterFlowService.switchToServerMode();
        return Result.success();
    }

    @GetMapping("/token-stats")
    public Result<Map<String, Integer>> getTokenStats() {
        return Result.success(clusterFlowService.getTokenStats());
    }
}
