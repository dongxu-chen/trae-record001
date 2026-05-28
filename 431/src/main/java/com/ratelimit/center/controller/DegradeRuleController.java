package com.ratelimit.center.controller;

import com.ratelimit.center.common.PageResult;
import com.ratelimit.center.common.Result;
import com.ratelimit.center.entity.DegradeRuleEntity;
import com.ratelimit.center.service.DegradeRuleService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/degrade-rules")
public class DegradeRuleController {

    @Autowired
    private DegradeRuleService degradeRuleService;

    @GetMapping
    public Result<PageResult<DegradeRuleEntity>> list(
            @RequestParam(required = false) String serviceName,
            @RequestParam(required = false) String resource,
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "20") Integer size) {
        return Result.success(degradeRuleService.list(serviceName, resource, page, size));
    }

    @GetMapping("/{id}")
    public Result<DegradeRuleEntity> getById(@PathVariable Long id) {
        return Result.success(degradeRuleService.getById(id));
    }

    @PostMapping
    public Result<Void> save(@RequestBody DegradeRuleEntity entity) {
        degradeRuleService.save(entity);
        return Result.success();
    }

    @PutMapping
    public Result<Void> update(@RequestBody DegradeRuleEntity entity) {
        degradeRuleService.update(entity);
        return Result.success();
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        degradeRuleService.delete(id);
        return Result.success();
    }

    @PatchMapping("/{id}/status")
    public Result<Void> updateStatus(@PathVariable Long id, @RequestParam Integer status) {
        degradeRuleService.updateStatus(id, status);
        return Result.success();
    }

    @PostMapping("/sync")
    public Result<Void> sync() {
        degradeRuleService.syncAllRulesToRedis();
        return Result.success();
    }
}
