package com.tracking.query.controller;

import com.tracking.common.model.DeviceBinding;
import com.tracking.common.model.MergeRequest;
import com.tracking.storage.dao.DeviceBindingDao;
import com.tracking.storage.dao.MergeRequestDao;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Api(tags = "设备绑定管理")
@RestController
@RequestMapping("/api/v1/devices")
public class DeviceBindingController {

    private final DeviceBindingDao deviceBindingDao;
    private final MergeRequestDao mergeRequestDao;

    public DeviceBindingController(DeviceBindingDao deviceBindingDao, MergeRequestDao mergeRequestDao) {
        this.deviceBindingDao = deviceBindingDao;
        this.mergeRequestDao = mergeRequestDao;
    }

    @ApiOperation("获取用户的设备绑定列表")
    @GetMapping("/user/{userId}")
    public ResponseEntity<Map<String, Object>> getUserDevices(
            @ApiParam("用户ID") @PathVariable String userId) {
        List<DeviceBinding> devices = deviceBindingDao.getDeviceBindingsByUserId(userId);
        
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("userId", userId);
        result.put("deviceCount", devices.size());
        result.put("devices", devices);
        
        return ResponseEntity.ok(result);
    }

    @ApiOperation("获取设备绑定详情")
    @GetMapping("/{userId}/{deviceId}")
    public ResponseEntity<Map<String, Object>> getDeviceBinding(
            @ApiParam("用户ID") @PathVariable String userId,
            @ApiParam("设备ID") @PathVariable String deviceId) {
        DeviceBinding binding = deviceBindingDao.getDeviceBinding(userId, deviceId);
        
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("data", binding);
        
        return ResponseEntity.ok(result);
    }

    @ApiOperation("停用设备绑定")
    @PostMapping("/{userId}/{deviceId}/deactivate")
    public ResponseEntity<Map<String, Object>> deactivateDevice(
            @ApiParam("用户ID") @PathVariable String userId,
            @ApiParam("设备ID") @PathVariable String deviceId) {
        deviceBindingDao.deactivateDevice(userId, deviceId);
        
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("message", "Device deactivated successfully");
        
        return ResponseEntity.ok(result);
    }

    @ApiOperation("获取待审核的合并请求列表")
    @GetMapping("/merge/pending")
    public ResponseEntity<Map<String, Object>> getPendingMergeRequests(
            @ApiParam("数量限制") @RequestParam(defaultValue = "20") int limit,
            @ApiParam("偏移量") @RequestParam(defaultValue = "0") int offset) {
        List<MergeRequest> requests = mergeRequestDao.getPendingMergeRequests(limit, offset);
        
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("total", requests.size());
        result.put("requests", requests);
        
        return ResponseEntity.ok(result);
    }

    @ApiOperation("获取合并请求详情")
    @GetMapping("/merge/{requestId}")
    public ResponseEntity<Map<String, Object>> getMergeRequest(
            @ApiParam("合并请求ID") @PathVariable String requestId) {
        MergeRequest request = mergeRequestDao.getMergeRequest(requestId);
        
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("data", request);
        
        return ResponseEntity.ok(result);
    }

    @ApiOperation("审核合并请求")
    @PostMapping("/merge/{requestId}/review")
    public ResponseEntity<Map<String, Object>> reviewMergeRequest(
            @ApiParam("合并请求ID") @PathVariable String requestId,
            @ApiParam("审核状态: approved/rejected") @RequestParam String status,
            @ApiParam("审核人") @RequestParam String reviewedBy,
            @ApiParam("审核备注") @RequestParam(required = false) String comment) {
        
        if (!"approved".equals(status) && !"rejected".equals(status)) {
            Map<String, Object> result = new HashMap<>();
            result.put("success", false);
            result.put("message", "Invalid status. Must be 'approved' or 'rejected'");
            return ResponseEntity.badRequest().body(result);
        }

        mergeRequestDao.updateMergeRequestStatus(requestId, status, reviewedBy, comment);
        
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("message", "Merge request " + status + " successfully");
        
        return ResponseEntity.ok(result);
    }

    @ApiOperation("获取用户的合并请求历史")
    @GetMapping("/merge/user/{userId}")
    public ResponseEntity<Map<String, Object>> getUserMergeRequests(
            @ApiParam("用户ID") @PathVariable String userId,
            @ApiParam("数量限制") @RequestParam(defaultValue = "20") int limit,
            @ApiParam("偏移量") @RequestParam(defaultValue = "0") int offset) {
        List<MergeRequest> requests = mergeRequestDao.getMergeRequestsByUser(userId, limit, offset);
        
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("userId", userId);
        result.put("total", requests.size());
        result.put("requests", requests);
        
        return ResponseEntity.ok(result);
    }
}
