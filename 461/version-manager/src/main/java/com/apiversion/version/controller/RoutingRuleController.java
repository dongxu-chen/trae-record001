package com.apiversion.version.controller;

import com.apiversion.version.entity.HeaderParseRule;
import com.apiversion.version.entity.RoutingRule;
import com.apiversion.version.service.RoutingRuleService;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/routing-rules")
@RequiredArgsConstructor
@Tag(name = "路由规则管理", description = "路由规则和Header解析规则的CRUD操作")
public class RoutingRuleController {

    private final RoutingRuleService routingRuleService;

    @GetMapping("/page")
    @Operation(summary = "分页查询路由规则", description = "分页查询路由规则列表，支持按API名称和状态筛选")
    public ResponseEntity<Map<String, Object>> listRules(
            @Parameter(description = "页码") @RequestParam(defaultValue = "1") Integer pageNum,
            @Parameter(description = "每页大小") @RequestParam(defaultValue = "10") Integer pageSize,
            @Parameter(description = "API名称（模糊查询）") @RequestParam(required = false) String apiName,
            @Parameter(description = "是否启用") @RequestParam(required = false) Boolean enabled) {
        Page<RoutingRule> page = new Page<>(pageNum, pageSize);
        IPage<RoutingRule> result = routingRuleService.listRules(page, apiName, enabled);
        return success(result);
    }

    @GetMapping("/{id}")
    @Operation(summary = "获取路由规则详情", description = "根据ID获取路由规则详细信息，包含Header解析规则")
    public ResponseEntity<Map<String, Object>> getRuleById(
            @Parameter(description = "规则ID") @PathVariable Long id) {
        RoutingRule rule = routingRuleService.getRuleById(id);
        return success(rule);
    }

    @GetMapping("/enabled")
    @Operation(summary = "获取所有启用的规则", description = "获取所有启用的路由规则列表")
    public ResponseEntity<Map<String, Object>> getEnabledRules() {
        List<RoutingRule> rules = routingRuleService.getEnabledRules();
        return success(rules);
    }

    @PostMapping
    @Operation(summary = "创建路由规则", description = "创建新的路由规则，可同时配置Header解析规则")
    public ResponseEntity<Map<String, Object>> createRule(@RequestBody RoutingRule rule) {
        RoutingRule created = routingRuleService.createRule(rule);
        return success(created);
    }

    @PutMapping
    @Operation(summary = "更新路由规则", description = "更新路由规则及其Header解析规则")
    public ResponseEntity<Map<String, Object>> updateRule(@RequestBody RoutingRule rule) {
        RoutingRule updated = routingRuleService.updateRule(rule);
        return success(updated);
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "删除路由规则", description = "删除路由规则及其关联的Header解析规则")
    public ResponseEntity<Map<String, Object>> deleteRule(
            @Parameter(description = "规则ID") @PathVariable Long id) {
        routingRuleService.deleteRule(id);
        return success(null);
    }

    @GetMapping("/{id}/header-rules")
    @Operation(summary = "获取Header解析规则", description = "获取指定路由规则的所有Header解析规则")
    public ResponseEntity<Map<String, Object>> getHeaderRules(
            @Parameter(description = "路由规则ID") @PathVariable Long id) {
        List<HeaderParseRule> rules = routingRuleService.getHeaderRulesByRoutingRuleId(id);
        return success(rules);
    }

    @PostMapping("/header-rules")
    @Operation(summary = "创建Header解析规则", description = "为指定路由规则创建Header解析规则")
    public ResponseEntity<Map<String, Object>> createHeaderRule(@RequestBody HeaderParseRule rule) {
        HeaderParseRule created = routingRuleService.createHeaderRule(rule);
        return success(created);
    }

    @PutMapping("/header-rules")
    @Operation(summary = "更新Header解析规则", description = "更新Header解析规则")
    public ResponseEntity<Map<String, Object>> updateHeaderRule(@RequestBody HeaderParseRule rule) {
        HeaderParseRule updated = routingRuleService.updateHeaderRule(rule);
        return success(updated);
    }

    @DeleteMapping("/header-rules/{id}")
    @Operation(summary = "删除Header解析规则", description = "删除指定的Header解析规则")
    public ResponseEntity<Map<String, Object>> deleteHeaderRule(
            @Parameter(description = "Header规则ID") @PathVariable Long id) {
        routingRuleService.deleteHeaderRule(id);
        return success(null);
    }

    @PostMapping("/sync/{apiPath}")
    @Operation(summary = "同步规则到Redis", description = "将指定API路径的路由规则同步到Redis，供网关使用")
    public ResponseEntity<Map<String, Object>> syncRulesToRedis(
            @Parameter(description = "API路径") @PathVariable String apiPath) {
        routingRuleService.syncHeaderRulesToRedis(apiPath);
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
