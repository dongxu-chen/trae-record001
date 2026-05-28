package com.ratelimit.center.controller;

import com.ratelimit.center.common.PageResult;
import com.ratelimit.center.common.Result;
import com.ratelimit.center.entity.ParamFlowRuleEntity;
import com.ratelimit.center.service.ParamFlowRuleService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/param-flow-rules")
public class ParamFlowRuleController {

    @Autowired
    private ParamFlowRuleService paramFlowRuleService;

    @GetMapping
    public Result<PageResult<ParamFlowRuleEntity>> list(
            @RequestParam(required = false) String serviceName,
            @RequestParam(required = false) String resource,
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "20") Integer size) {
        return Result.success(paramFlowRuleService.list(serviceName, resource, page, size));
    }

    @GetMapping("/{id}")
    public Result<ParamFlowRuleEntity> getById(@PathVariable Long id) {
        return Result.success(paramFlowRuleService.getById(id));
    }

    @PostMapping
    public Result<Void> save(@RequestBody ParamFlowRuleEntity entity) {
        paramFlowRuleService.save(entity);
        return Result.success();
    }

    @PutMapping
    public Result<Void> update(@RequestBody ParamFlowRuleEntity entity) {
        paramFlowRuleService.update(entity);
        return Result.success();
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        paramFlowRuleService.delete(id);
        return Result.success();
    }

    @PatchMapping("/{id}/status")
    public Result<Void> updateStatus(@PathVariable Long id, @RequestParam Integer status) {
        paramFlowRuleService.updateStatus(id, status);
        return Result.success();
    }

    @PostMapping("/sync")
    public Result<Void> sync() {
        paramFlowRuleService.syncAllRulesToRedis();
        return Result.success();
    }
}
