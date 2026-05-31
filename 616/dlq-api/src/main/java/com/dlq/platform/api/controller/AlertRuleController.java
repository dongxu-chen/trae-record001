package com.dlq.platform.api.controller;

import com.dlq.platform.api.common.Result;
import com.dlq.platform.common.dto.AlertRuleDTO;
import com.dlq.platform.common.entity.AlertRule;
import com.dlq.platform.common.enums.AlertLevelEnum;
import com.dlq.platform.service.AlertService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/alert-rules")
@RequiredArgsConstructor
public class AlertRuleController {

    private final AlertService alertService;

    @GetMapping
    public Result<Map<String, Object>> list(
            @RequestParam(required = false) String name,
            @RequestParam(required = false) Boolean enabled,
            @RequestParam(required = false) String notificationType,
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize) {
        AlertRuleDTO query = AlertRuleDTO.builder()
                .name(name)
                .enabled(enabled)
                .notificationType(notificationType)
                .pageNum(pageNum)
                .pageSize(pageSize)
                .build();
        Map<String, Object> result = alertService.queryAlertRules(query);
        return Result.success(result);
    }

    @GetMapping("/{id}")
    public Result<AlertRule> getById(@PathVariable String id) {
        AlertRule rule = alertService.getAlertRule(id);
        return Result.success(rule);
    }

    @PostMapping
    public Result<AlertRule> create(@Valid @RequestBody AlertRule rule) {
        if (rule.getId() == null) {
            rule.setId(java.util.UUID.randomUUID().toString().replace("-", ""));
        }
        if (rule.getCreateTime() == null) {
            rule.setCreateTime(LocalDateTime.now());
        }
        rule.setUpdateTime(LocalDateTime.now());
        AlertRule created = alertService.createAlertRule(rule);
        return Result.success("创建成功", created);
    }

    @PutMapping("/{id}")
    public Result<AlertRule> update(@PathVariable String id, @Valid @RequestBody AlertRule rule) {
        rule.setId(id);
        rule.setUpdateTime(LocalDateTime.now());
        AlertRule updated = alertService.updateAlertRule(rule);
        return Result.success("更新成功", updated);
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable String id) {
        alertService.deleteAlertRule(id);
        return Result.success("删除成功");
    }

    @PostMapping("/{id}/enable")
    public Result<AlertRule> enable(@PathVariable String id) {
        AlertRule rule = alertService.getAlertRule(id);
        rule.setEnabled(true);
        rule.setUpdateTime(LocalDateTime.now());
        AlertRule updated = alertService.updateAlertRule(rule);
        return Result.success("启用成功", updated);
    }

    @PostMapping("/{id}/disable")
    public Result<AlertRule> disable(@PathVariable String id) {
        AlertRule rule = alertService.getAlertRule(id);
        rule.setEnabled(false);
        rule.setUpdateTime(LocalDateTime.now());
        AlertRule updated = alertService.updateAlertRule(rule);
        return Result.success("禁用成功", updated);
    }

    @GetMapping("/{id}/history")
    public Result<Map<String, Object>> history(
            @PathVariable String id,
            @RequestParam(required = false) AlertLevelEnum level,
            @RequestParam(required = false) LocalDateTime startTime,
            @RequestParam(required = false) LocalDateTime endTime,
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize) {
        Map<String, Object> result = alertService.queryAlertHistory(id, level, startTime, endTime, pageNum, pageSize);
        return Result.success(result);
    }
}
