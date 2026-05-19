package com.scheduler.controller;

import com.scheduler.common.Result;
import com.scheduler.raft.ClusterManager;
import com.scheduler.raft.RaftMessage;
import com.scheduler.raft.SchedulerManager;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/cluster")
public class ClusterController {

    @Resource
    private ClusterManager clusterManager;

    @Resource
    private SchedulerManager schedulerManager;

    @PostMapping("/join")
    public Result<RaftMessage.ClusterJoinResponse> handleJoin(@RequestBody RaftMessage.ClusterJoinRequest request) {
        RaftMessage.ClusterJoinResponse response = clusterManager.handleJoinRequest(request);
        return Result.success(response);
    }

    @PostMapping("/join/bootstrap")
    public Result<Void> joinCluster(@RequestParam String bootstrapAddress) {
        boolean success = clusterManager.joinCluster(bootstrapAddress);
        if (success) {
            return Result.success();
        }
        return Result.error("加入集群失败");
    }

    @PostMapping("/leave")
    public Result<Void> leaveCluster() {
        clusterManager.leaveCluster();
        return Result.success();
    }

    @GetMapping("/members")
    public Result<List<Map<String, String>>> getClusterMembers() {
        List<Map<String, String>> members = clusterManager.getClusterMembers();
        return Result.success(members);
    }

    @GetMapping("/status")
    public Result<Map<String, Object>> getClusterStatus() {
        Map<String, Object> status = new HashMap<>();
        status.put("isLeader", clusterManager.isLeader());
        status.put("currentLeader", clusterManager.getCurrentLeader());
        status.put("schedulerStatus", schedulerManager.getSchedulerStatus());
        status.put("schedulerActive", schedulerManager.isSchedulerActive());
        return Result.success(status);
    }

    @GetMapping("/raft/info")
    public Result<Map<String, String>> getRaftInfo(HttpServletRequest request) {
        Map<String, String> info = new HashMap<>();
        info.putAll(clusterManager.getClusterMembers().get(0));
        return Result.success(info);
    }
}
