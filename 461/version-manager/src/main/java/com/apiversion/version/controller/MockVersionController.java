package com.apiversion.version.controller;

import com.apiversion.version.entity.MockVersionConfig;
import com.apiversion.version.service.MockVersionService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/mock-configs")
@Tag(name = "Mock版本管理", description = "Mock历史版本配置管理API")
public class MockVersionController {

    private final MockVersionService mockVersionService;

    public MockVersionController(MockVersionService mockVersionService) {
        this.mockVersionService = mockVersionService;
    }

    @PostMapping
    @Operation(summary = "创建Mock配置", description = "创建新的Mock版本接口配置")
    public ResponseEntity<Map<String, Object>> createMockConfig(@RequestBody MockVersionConfig config) {
        MockVersionConfig created = mockVersionService.createMockConfig(config);
        return success(created);
    }

    @PutMapping
    @Operation(summary = "更新Mock配置", description = "更新已有的Mock配置")
    public ResponseEntity<Map<String, Object>> updateMockConfig(@RequestBody MockVersionConfig config) {
        MockVersionConfig updated = mockVersionService.updateMockConfig(config);
        return success(updated);
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "删除Mock配置", description = "删除指定的Mock配置")
    public ResponseEntity<Map<String, Object>> deleteMockConfig(
            @Parameter(description = "配置ID") @PathVariable Long id) {
        mockVersionService.deleteMockConfig(id);
        return success(null);
    }

    @GetMapping("/{id}")
    @Operation(summary = "获取Mock配置详情", description = "根据ID获取Mock配置详细信息")
    public ResponseEntity<Map<String, Object>> getMockConfigById(
            @Parameter(description = "配置ID") @PathVariable Long id) {
        MockVersionConfig config = mockVersionService.getMockConfigById(id);
        return success(config);
    }

    @GetMapping("/version/{versionId}")
    @Operation(summary = "获取版本的所有Mock配置", description = "根据版本ID获取该版本的所有Mock配置")
    public ResponseEntity<Map<String, Object>> getMockConfigsByVersionId(
            @Parameter(description = "版本ID") @PathVariable Long versionId) {
        List<MockVersionConfig> configs = mockVersionService.getMockConfigsByVersionId(versionId);
        return success(configs);
    }

    @GetMapping("/path")
    @Operation(summary = "获取路径的Mock配置", description = "根据接口路径获取相关的Mock配置")
    public ResponseEntity<Map<String, Object>> getMockConfigsByPath(
            @Parameter(description = "接口路径") @RequestParam String path) {
        List<MockVersionConfig> configs = mockVersionService.getMockConfigsByPath(path);
        return success(configs);
    }

    @PostMapping("/{id}/toggle")
    @Operation(summary = "切换Mock配置启用状态", description = "启用或禁用指定的Mock配置")
    public ResponseEntity<Map<String, Object>> toggleMockConfig(
            @Parameter(description = "配置ID") @PathVariable Long id,
            @Parameter(description = "是否启用") @RequestParam boolean enabled) {
        MockVersionConfig config = mockVersionService.toggleMockConfig(id, enabled);
        return success(config);
    }

    @PostMapping("/{id}/sync")
    @Operation(summary = "同步Mock配置到Redis", description = "将Mock配置同步到网关Redis缓存")
    public ResponseEntity<Map<String, Object>> syncMockConfig(
            @Parameter(description = "配置ID") @PathVariable Long id) {
        mockVersionService.syncMockConfigToRedis(id);
        return success("同步成功");
    }

    @GetMapping("/enabled")
    @Operation(summary = "获取所有启用的Mock配置", description = "获取所有已启用的Mock配置列表")
    public ResponseEntity<Map<String, Object>> getAllEnabledMockConfigs() {
        List<MockVersionConfig> configs = mockVersionService.getAllEnabledMockConfigs();
        return success(configs);
    }

    private ResponseEntity<Map<String, Object>> success(Object data) {
        Map<String, Object> result = new HashMap<>();
        result.put("code", 200);
        result.put("message", "success");
        result.put("data", data);
        return ResponseEntity.ok(result);
    }
}
