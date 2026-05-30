package com.apiversion.version.controller;

import com.apiversion.version.entity.ApiVersion;
import com.apiversion.version.service.ApiVersionService;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/versions")
@Tag(name = "API版本管理", description = "API版本的CRUD、发布、废弃、下线等操作")
public class ApiVersionController {

    private final ApiVersionService versionService;

    public ApiVersionController(ApiVersionService versionService) {
        this.versionService = versionService;
    }

    @PostMapping
    @Operation(summary = "创建版本", description = "创建新的API版本草稿")
    public ResponseEntity<Map<String, Object>> createVersion(@RequestBody ApiVersion version) {
        ApiVersion created = versionService.createVersion(version);
        return success(created);
    }

    @PutMapping
    @Operation(summary = "更新版本", description = "更新草稿状态的版本信息")
    public ResponseEntity<Map<String, Object>> updateVersion(@RequestBody ApiVersion version) {
        ApiVersion updated = versionService.updateVersion(version);
        return success(updated);
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "删除版本", description = "删除草稿状态的版本")
    public ResponseEntity<Map<String, Object>> deleteVersion(
            @Parameter(description = "版本ID") @PathVariable Long id) {
        versionService.deleteVersion(id);
        return success(null);
    }

    @GetMapping("/{id}")
    @Operation(summary = "获取版本详情", description = "根据ID获取版本详细信息")
    public ResponseEntity<Map<String, Object>> getVersionById(
            @Parameter(description = "版本ID") @PathVariable Long id) {
        ApiVersion version = versionService.getVersionById(id);
        return success(version);
    }

    @GetMapping("/service/{serviceName}")
    @Operation(summary = "获取服务的所有版本", description = "根据服务名称获取该服务的所有版本列表")
    public ResponseEntity<Map<String, Object>> getVersionByServiceName(
            @Parameter(description = "服务名称") @PathVariable String serviceName) {
        List<ApiVersion> versions = versionService.getVersionByServiceName(serviceName);
        return success(versions);
    }

    @GetMapping("/page")
    @Operation(summary = "分页查询版本列表", description = "分页查询版本，支持按服务名称和状态筛选")
    public ResponseEntity<Map<String, Object>> listVersions(
            @Parameter(description = "页码") @RequestParam(defaultValue = "1") Integer pageNum,
            @Parameter(description = "每页大小") @RequestParam(defaultValue = "10") Integer pageSize,
            @Parameter(description = "服务名称（模糊查询）") @RequestParam(required = false) String serviceName,
            @Parameter(description = "状态") @RequestParam(required = false) String status) {
        Page<ApiVersion> page = new Page<>(pageNum, pageSize);
        IPage<ApiVersion> result = versionService.listVersions(page, serviceName, status);
        return success(result);
    }

    @PostMapping("/{id}/publish")
    @Operation(summary = "发布版本", description = "将草稿状态的版本发布")
    public ResponseEntity<Map<String, Object>> publishVersion(
            @Parameter(description = "版本ID") @PathVariable Long id) {
        ApiVersion version = versionService.publishVersion(id);
        return success(version);
    }

    @PostMapping("/{id}/deprecate")
    @Operation(summary = "废弃版本", description = "将已发布的版本标记为废弃")
    public ResponseEntity<Map<String, Object>> deprecateVersion(
            @Parameter(description = "版本ID") @PathVariable Long id) {
        ApiVersion version = versionService.deprecateVersion(id);
        return success(version);
    }

    @PostMapping("/{id}/offline")
    @Operation(summary = "下线版本", description = "将已废弃的版本下线")
    public ResponseEntity<Map<String, Object>> offlineVersion(
            @Parameter(description = "版本ID") @PathVariable Long id) {
        ApiVersion version = versionService.offlineVersion(id);
        return success(version);
    }

    @PostMapping("/{id}/default")
    @Operation(summary = "设置默认版本", description = "将已发布的版本设为默认版本")
    public ResponseEntity<Map<String, Object>> setDefaultVersion(
            @Parameter(description = "版本ID") @PathVariable Long id) {
        ApiVersion version = versionService.setDefaultVersion(id);
        return success(version);
    }

    @GetMapping("/service/{serviceName}/default")
    @Operation(summary = "获取服务的默认版本", description = "根据服务名称获取其默认版本")
    public ResponseEntity<Map<String, Object>> getDefaultVersion(
            @Parameter(description = "服务名称") @PathVariable String serviceName) {
        ApiVersion version = versionService.getDefaultVersion(serviceName);
        return success(version);
    }

    @PostMapping("/{id}/deprecation-schedule")
    @Operation(summary = "更新废弃时间表", description = "设置版本的计划下线时间和废弃提示信息")
    public ResponseEntity<Map<String, Object>> updateDeprecationSchedule(
            @Parameter(description = "版本ID") @PathVariable Long id,
            @RequestBody Map<String, Object> request) {
        java.time.LocalDateTime plannedRetireTime = request.get("plannedRetireTime") != null ?
                java.time.LocalDateTime.parse((String) request.get("plannedRetireTime")) : null;
        String deprecationMessage = (String) request.get("deprecationMessage");
        ApiVersion version = versionService.updateDeprecationSchedule(id, plannedRetireTime, deprecationMessage);
        return success(version);
    }

    @GetMapping("/deprecated")
    @Operation(summary = "获取废弃版本列表", description = "获取所有已废弃或已下线的版本及其下线时间表")
    public ResponseEntity<Map<String, Object>> getDeprecatedVersions() {
        List<ApiVersion> versions = versionService.getDeprecatedVersions();
        return success(versions);
    }

    @GetMapping("/stats")
    @Operation(summary = "获取版本调用统计", description = "获取各版本的调用量统计和趋势数据")
    public ResponseEntity<Map<String, Object>> getVersionCallStats(
            @Parameter(description = "服务名称") @RequestParam(required = false) String serviceName,
            @Parameter(description = "开始日期(yyyy-MM-dd)") @RequestParam(required = false) String startDate,
            @Parameter(description = "结束日期(yyyy-MM-dd)") @RequestParam(required = false) String endDate) {
        Map<String, Object> stats = versionService.getVersionCallStats(serviceName, startDate, endDate);
        return success(stats);
    }

    @PostMapping("/{id}/sync-deprecation-config")
    @Operation(summary = "同步废弃配置到Redis", description = "将版本的废弃配置同步到Redis网关")
    public ResponseEntity<Map<String, Object>> syncDeprecationConfig(
            @Parameter(description = "版本ID") @PathVariable Long id) {
        versionService.syncDeprecationConfigToRedis(id);
        return success("同步成功");
    }

    private ResponseEntity<Map<String, Object>> success(Object data) {
        Map<String, Object> result = new HashMap<>();
        result.put("code", 200);
        result.put("message", "success");
        result.put("data", data);
        return ResponseEntity.ok(result);
    }
}
