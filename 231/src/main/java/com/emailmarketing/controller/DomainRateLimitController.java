package com.emailmarketing.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.emailmarketing.common.Result;
import com.emailmarketing.entity.DomainRateLimit;
import com.emailmarketing.service.DomainRateLimitService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/rate-limits")
public class DomainRateLimitController {

    @Autowired
    private DomainRateLimitService rateLimitService;

    @GetMapping
    public Result<Page<DomainRateLimit>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String domain) {
        Page<DomainRateLimit> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<DomainRateLimit> wrapper = new LambdaQueryWrapper<>();
        if (domain != null && !domain.isEmpty()) {
            wrapper.like(DomainRateLimit::getDomain, domain);
        }
        wrapper.orderByDesc(DomainRateLimit::getCreatedAt);
        return Result.success(rateLimitService.page(pageParam, wrapper));
    }

    @GetMapping("/all")
    public Result<List<DomainRateLimit>> getAll() {
        return Result.success(rateLimitService.getAllDomainLimits());
    }

    @GetMapping("/domain/{domain}")
    public Result<DomainRateLimit> getByDomain(@PathVariable String domain) {
        return Result.success(rateLimitService.getOrCreateDomainLimit(domain));
    }

    @GetMapping("/{id}")
    public Result<DomainRateLimit> getById(@PathVariable Long id) {
        return Result.success(rateLimitService.getById(id));
    }

    @PostMapping
    public Result<Void> create(@RequestBody DomainRateLimit rateLimit) {
        rateLimit.setStatus(1);
        boolean success = rateLimitService.save(rateLimit);
        if (success) {
            rateLimitService.refreshDomainLimitCache();
        }
        return success ? Result.success() : Result.error("创建失败");
    }

    @PostMapping("/domain/{domain}")
    public Result<Void> createOrUpdateByDomain(
            @PathVariable String domain,
            @RequestParam int limitPerMinute) {
        boolean success = rateLimitService.updateDomainLimit(domain, limitPerMinute);
        return success ? Result.success() : Result.error("配置失败");
    }

    @PutMapping
    public Result<Void> update(@RequestBody DomainRateLimit rateLimit) {
        boolean success = rateLimitService.updateById(rateLimit);
        if (success) {
            rateLimitService.refreshDomainLimitCache();
        }
        return success ? Result.success() : Result.error("更新失败");
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        boolean success = rateLimitService.removeById(id);
        if (success) {
            rateLimitService.refreshDomainLimitCache();
        }
        return success ? Result.success() : Result.error("删除失败");
    }

    @PutMapping("/{id}/status")
    public Result<Void> updateStatus(@PathVariable Long id, @RequestParam Integer status) {
        DomainRateLimit rateLimit = new DomainRateLimit();
        rateLimit.setId(id);
        rateLimit.setStatus(status);
        boolean success = rateLimitService.updateById(rateLimit);
        if (success) {
            rateLimitService.refreshDomainLimitCache();
        }
        return success ? Result.success() : Result.error("状态更新失败");
    }

    @PostMapping("/refresh")
    public Result<Void> refreshCache() {
        rateLimitService.refreshDomainLimitCache();
        return Result.success();
    }

    @GetMapping("/check/{email}")
    public Result<Map<String, Object>> checkLimit(@PathVariable String email) {
        Map<String, Object> result = new HashMap<>();
        String domain = email.contains("@") ? email.substring(email.indexOf("@") + 1) : email;
        int limit = rateLimitService.getLimitForDomain(domain);
        result.put("domain", domain);
        result.put("limitPerMinute", limit);
        return Result.success(result);
    }
}
