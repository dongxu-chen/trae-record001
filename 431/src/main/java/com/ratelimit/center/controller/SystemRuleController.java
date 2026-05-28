package com.ratelimit.center.controller;

import com.ratelimit.center.common.PageResult;
import com.ratelimit.center.common.Result;
import com.ratelimit.center.entity.SystemRuleEntity;
import com.ratelimit.center.service.SystemRuleService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/system-rules")
public class SystemRuleController {

    @Autowired
    private SystemRuleService systemRuleService;

    @GetMapping
    public Result<PageResult<SystemRuleEntity>> list(
            @RequestParam(required = false) String serviceName,
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "20") Integer size) {
        return Result.success(systemRuleService.list(serviceName, page, size));
    }

    @GetMapping("/{id}")
    public Result<SystemRuleEntity> getById(@PathVariable Long id) {
        return Result.success(systemRuleService.getById(id));
    }

    @PostMapping
    public Result<Void> save(@RequestBody SystemRuleEntity entity) {
        systemRuleService.save(entity);
        return Result.success();
    }

    @PutMapping
    public Result<Void> update(@RequestBody SystemRuleEntity entity) {
        systemRuleService.update(entity);
        return Result.success();
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        systemRuleService.delete(id);
        return Result.success();
    }

    @PatchMapping("/{id}/status")
    public Result<Void> updateStatus(@PathVariable Long id, @RequestParam Integer status) {
        systemRuleService.updateStatus(id, status);
        return Result.success();
    }

    @PostMapping("/sync")
    public Result<Void> sync() {
        systemRuleService.syncAllRulesToRedis();
        return Result.success();
    }
}
