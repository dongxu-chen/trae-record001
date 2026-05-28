package com.ratelimit.center.controller;

import com.ratelimit.center.common.PageResult;
import com.ratelimit.center.common.Result;
import com.ratelimit.center.entity.FlowRuleEntity;
import com.ratelimit.center.service.FlowRuleService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/flow-rules")
public class FlowRuleController {

    @Autowired
    private FlowRuleService flowRuleService;

    @GetMapping
    public Result<PageResult<FlowRuleEntity>> list(
            @RequestParam(required = false) String serviceName,
            @RequestParam(required = false) String resource,
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "20") Integer size) {
        return Result.success(flowRuleService.list(serviceName, resource, page, size));
    }

    @GetMapping("/{id}")
    public Result<FlowRuleEntity> getById(@PathVariable Long id) {
        return Result.success(flowRuleService.getById(id));
    }

    @PostMapping
    public Result<Void> save(@RequestBody FlowRuleEntity entity) {
        flowRuleService.save(entity);
        return Result.success();
    }

    @PutMapping
    public Result<Void> update(@RequestBody FlowRuleEntity entity) {
        flowRuleService.update(entity);
        return Result.success();
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        flowRuleService.delete(id);
        return Result.success();
    }

    @PatchMapping("/{id}/status")
    public Result<Void> updateStatus(@PathVariable Long id, @RequestParam Integer status) {
        flowRuleService.updateStatus(id, status);
        return Result.success();
    }

    @PostMapping("/sync")
    public Result<Void> sync() {
        flowRuleService.syncAllRulesToRedis();
        return Result.success();
    }
}
