package com.risk.engine.controller;

import com.risk.engine.entity.FeatureSnapshot;
import com.risk.engine.service.FeatureSnapshotService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/features")
@Api(tags = "特征回溯")
public class FeatureHistoryController {

    @Autowired
    private FeatureSnapshotService snapshotService;

    @GetMapping("/history/{requestId}")
    @ApiOperation("根据请求ID查询特征历史")
    public ResponseEntity<Map<String, Object>> getFeatureHistory(@PathVariable String requestId) {
        return ResponseEntity.ok(snapshotService.getFeatureHistory(requestId));
    }

    @GetMapping("/user/{userId}")
    @ApiOperation("查询用户历史记录")
    public ResponseEntity<List<FeatureSnapshot>> getUserHistory(@PathVariable String userId,
                                                                 @RequestParam(defaultValue = "100") int limit) {
        return ResponseEntity.ok(snapshotService.getUserHistory(userId, limit));
    }

    @GetMapping("/user/{userId}/page")
    @ApiOperation("分页查询用户历史记录")
    public ResponseEntity<Page<FeatureSnapshot>> getUserHistoryPaged(@PathVariable String userId,
                                                                       @RequestParam(defaultValue = "0") int page,
                                                                       @RequestParam(defaultValue = "10") int size) {
        return ResponseEntity.ok(snapshotService.getUserHistoryPaged(userId, page, size));
    }

    @GetMapping("/compare")
    @ApiOperation("对比两次请求的特征差异")
    public ResponseEntity<Map<String, Object>> compareSnapshots(@RequestParam String requestId1,
                                                                  @RequestParam String requestId2) {
        return ResponseEntity.ok(snapshotService.compareSnapshots(requestId1, requestId2));
    }

    @GetMapping("/recent")
    @ApiOperation("获取最近的快照")
    public ResponseEntity<List<FeatureSnapshot>> getRecentSnapshots(@RequestParam(defaultValue = "100") int limit) {
        return ResponseEntity.ok(snapshotService.getRecentSnapshots(limit));
    }

    @GetMapping("/scene/{scene}/decision")
    @ApiOperation("按场景和决策结果查询快照")
    public ResponseEntity<Page<FeatureSnapshot>> getSnapshotsBySceneAndDecision(@PathVariable String scene,
                                                                                  @RequestParam String decision,
                                                                                  @RequestParam(defaultValue = "0") int page,
                                                                                  @RequestParam(defaultValue = "10") int size) {
        return ResponseEntity.ok(snapshotService.getSnapshotsBySceneAndDecision(scene, decision, page, size));
    }
}
