package com.quota.management.controller;

import com.quota.management.common.Result;
import com.quota.management.entity.PoolMemberAllocation;
import com.quota.management.entity.QuotaPool;
import com.quota.management.service.QuotaPoolService;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/pool")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class QuotaPoolController {

    private final QuotaPoolService quotaPoolService;

    @PostMapping
    public Result<QuotaPool> createPool(@RequestBody QuotaPool pool) {
        QuotaPool created = quotaPoolService.createPool(pool);
        return Result.success(created);
    }

    @GetMapping("/{poolId}")
    public Result<QuotaPool> getPool(@PathVariable String poolId) {
        QuotaPool pool = quotaPoolService.getPool(poolId);
        if (pool == null) {
            return Result.error(404, "Pool not found");
        }
        return Result.success(pool);
    }

    @PutMapping
    public Result<QuotaPool> updatePool(@RequestBody QuotaPool pool) {
        try {
            QuotaPool updated = quotaPoolService.updatePool(pool);
            return Result.success(updated);
        } catch (RuntimeException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @DeleteMapping("/{poolId}")
    public Result<Void> deletePool(@PathVariable String poolId) {
        quotaPoolService.deletePool(poolId);
        return Result.success(null);
    }

    @GetMapping("/list")
    public Result<List<QuotaPool>> getAllPools() {
        List<QuotaPool> pools = quotaPoolService.getAllPools();
        return Result.success(pools);
    }

    @PostMapping("/{poolId}/member")
    public Result<Void> addMember(@PathVariable String poolId, @RequestBody MemberRequest request) {
        try {
            quotaPoolService.addMember(poolId, request.getTenantId(), request.getWeight());
            return Result.success(null);
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    @DeleteMapping("/{poolId}/member/{tenantId}")
    public Result<Void> removeMember(@PathVariable String poolId, @PathVariable String tenantId) {
        try {
            quotaPoolService.removeMember(poolId, tenantId);
            return Result.success(null);
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    @GetMapping("/{poolId}/members")
    public Result<List<PoolMemberAllocation>> getPoolMembers(@PathVariable String poolId) {
        List<PoolMemberAllocation> members = quotaPoolService.getPoolMembers(poolId);
        return Result.success(members);
    }

    @GetMapping("/{poolId}/stats")
    public Result<Map<String, Object>> getPoolStats(@PathVariable String poolId) {
        Map<String, Object> stats = quotaPoolService.getPoolStats(poolId);
        if (stats == null) {
            return Result.error(404, "Pool not found");
        }
        return Result.success(stats);
    }

    @PostMapping("/{poolId}/consume")
    public Result<Object> consumeFromPool(@PathVariable String poolId, @RequestBody ConsumeRequest request) {
        Object result = quotaPoolService.consumeFromPool(
                poolId, request.getTenantId(), request.getGranularity(), request.getAmount());
        return Result.success(result);
    }

    @Data
    public static class MemberRequest {
        private String tenantId;
        private Double weight;
    }

    @Data
    public static class ConsumeRequest {
        private String tenantId;
        private String granularity;
        private long amount;
    }
}
