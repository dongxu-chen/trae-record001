package com.distid.controller;

import com.distid.ha.CrossDcSyncService;
import com.distid.ha.DatacenterNode;
import com.distid.ha.DatacenterRegistry;
import com.distid.ha.FailoverManager;
import com.distid.snowflake.SnowflakeIdService;
import com.distid.tracking.IdLifecycleEvent;
import com.distid.tracking.IdLifecycleTracker;
import com.distid.readable.Base62Codec;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@Slf4j
@RestController
@RequestMapping("/api")
public class ExtendedApiController {

    private final SnowflakeIdService snowflakeIdService;
    private final IdLifecycleTracker tracker;
    private final DatacenterRegistry dcRegistry;
    private final FailoverManager failoverManager;

    public ExtendedApiController(SnowflakeIdService snowflakeIdService,
                                  IdLifecycleTracker tracker,
                                  DatacenterRegistry dcRegistry,
                                  FailoverManager failoverManager) {
        this.snowflakeIdService = snowflakeIdService;
        this.tracker = tracker;
        this.dcRegistry = dcRegistry;
        this.failoverManager = failoverManager;
    }

    @GetMapping("/id/lifecycle/{id}")
    public ResponseEntity<Map<String, Object>> getLifecycle(@PathVariable long id) {
        List<IdLifecycleEvent> events = tracker.getLifecycle(id);
        Map<String, Object> result = new HashMap<>();
        result.put("id", id);
        result.put("base62", Base62Codec.encode(id));
        result.put("events", events);
        result.put("trackingEnabled", tracker.isTrackingEnabled());
        return ResponseEntity.ok(result);
    }

    @GetMapping("/id/lifecycle/trace/{traceId}")
    public ResponseEntity<Map<String, Object>> getByTraceId(@PathVariable String traceId) {
        Set<String> ids = tracker.getIdsByTraceId(traceId);
        Map<String, Object> result = new HashMap<>();
        result.put("traceId", traceId);
        result.put("idCount", ids.size());
        result.put("ids", ids);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/id/lifecycle/biz/{bizTag}")
    public ResponseEntity<Map<String, Object>> getByBizTag(@PathVariable String bizTag,
                                                            @RequestParam(defaultValue = "100") int limit) {
        Set<String> ids = tracker.getIdsByBizTag(bizTag, 0, limit);
        Map<String, Object> result = new HashMap<>();
        result.put("bizTag", bizTag);
        result.put("idCount", ids.size());
        result.put("ids", ids);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/dc/status")
    public ResponseEntity<Map<String, Object>> dcStatus() {
        Map<String, Object> status = new HashMap<>();
        status.put("localDc", dcRegistry.getLocalDcCode());
        status.put("localStatus", dcRegistry.getLocalStatus().name());
        status.put("segmentOffset", dcRegistry.getSegmentOffset());
        status.put("segmentStep", dcRegistry.getSegmentStep());

        List<Map<String, Object>> remotes = new ArrayList<>();
        for (DatacenterNode node : dcRegistry.getRemoteDatacenters()) {
            Map<String, Object> remote = new HashMap<>();
            remote.put("dcCode", node.getDcCode());
            remote.put("region", node.getRegion());
            remote.put("status", node.getStatus().name());
            remote.put("priority", node.getPriority());
            remote.put("segmentOffset", node.getSegmentOffset());
            remotes.add(remote);
        }
        status.put("remoteDatacenters", remotes);
        status.put("failoverStatus", failoverManager.getFailoverStatus());
        return ResponseEntity.ok(status);
    }

    @GetMapping("/dc/failover")
    public ResponseEntity<Map<String, Object>> failoverInfo() {
        Map<String, Object> info = new HashMap<>();
        info.put("status", failoverManager.getFailoverStatus());

        DatacenterNode target = failoverManager.findFailoverTarget();
        if (target != null) {
            Map<String, Object> targetInfo = new HashMap<>();
            targetInfo.put("dcCode", target.getDcCode());
            targetInfo.put("region", target.getRegion());
            targetInfo.put("priority", target.getPriority());
            info.put("failoverTarget", targetInfo);
        } else {
            info.put("failoverTarget", "none");
        }
        return ResponseEntity.ok(info);
    }

    @GetMapping("/id/health")
    public ResponseEntity<Map<String, Object>> health() {
        Map<String, Object> health = new HashMap<>();
        health.put("status", "UP");
        health.put("workerId", snowflakeIdService.getWorkerId());
        health.put("podName", snowflakeIdService.getPodName());
        health.put("dcCode", dcRegistry.getLocalDcCode());
        health.put("ntpSynchronized", snowflakeIdService.isNtpSynchronized());
        return ResponseEntity.ok(health);
    }
}
