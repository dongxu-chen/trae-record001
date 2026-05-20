package com.filestorage.controller;

import com.filestorage.common.Result;
import com.filestorage.entity.Tenant;
import com.filestorage.service.TenantService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import jakarta.annotation.Resource;

@Slf4j
@RestController
@RequestMapping("/api/tenant")
public class TenantController {

    @Resource
    private TenantService tenantService;

    @PostMapping("/create")
    public Result<Tenant> createTenant(
            @RequestParam String tenantCode,
            @RequestParam String tenantName,
            @RequestParam(defaultValue = "0") Long storageQuota) {
        try {
            Tenant tenant = tenantService.createTenant(tenantCode, tenantName, storageQuota);
            return Result.success(tenant);
        } catch (Exception e) {
            log.error("创建租户失败", e);
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/{tenantCode}")
    public Result<Tenant> getTenant(@PathVariable String tenantCode) {
        try {
            Tenant tenant = tenantService.getTenantByCode(tenantCode);
            return Result.success(tenant);
        } catch (Exception e) {
            log.error("获取租户信息失败", e);
            return Result.error(e.getMessage());
        }
    }
}
