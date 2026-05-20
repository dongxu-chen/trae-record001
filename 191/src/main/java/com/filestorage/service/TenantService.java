package com.filestorage.service;

import com.filestorage.entity.Tenant;
import com.filestorage.repository.TenantRepository;
import com.filestorage.util.RedisUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import jakarta.annotation.Resource;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class TenantService {

    private static final String TENANT_CACHE_PREFIX = "tenant:";

    @Resource
    private TenantRepository tenantRepository;

    @Resource
    private RedisUtil redisUtil;

    @Resource
    private MinioStorageService minioStorageService;

    public Tenant getTenantByCode(String tenantCode) {
        String cacheKey = TENANT_CACHE_PREFIX + tenantCode;
        Object cached = redisUtil.get(cacheKey);
        if (cached != null) {
            return (Tenant) cached;
        }

        Tenant tenant = tenantRepository.findByTenantCode(tenantCode)
                .orElseThrow(() -> new RuntimeException("租户不存在: " + tenantCode));

        redisUtil.set(cacheKey, tenant, 1, TimeUnit.HOURS);
        return tenant;
    }

    @Transactional
    public Tenant createTenant(String tenantCode, String tenantName, Long storageQuota) {
        if (tenantRepository.existsByTenantCode(tenantCode)) {
            throw new RuntimeException("租户编码已存在: " + tenantCode);
        }

        Tenant tenant = new Tenant();
        tenant.setTenantCode(tenantCode);
        tenant.setTenantName(tenantName);
        tenant.setStorageQuota(storageQuota);
        tenant = tenantRepository.save(tenant);

        String bucketName = minioStorageService.getBucketName(tenantCode);
        minioStorageService.createBucketIfNotExists(bucketName);

        return tenant;
    }

    @Transactional
    public boolean increaseUsedStorage(String tenantCode, long size) {
        Tenant tenant = getTenantByCode(tenantCode);
        if (tenant.getStorageQuota() > 0 &&
                tenant.getUsedStorage() + size > tenant.getStorageQuota()) {
            return false;
        }
        tenant.setUsedStorage(tenant.getUsedStorage() + size);
        tenantRepository.save(tenant);
        redisUtil.delete(TENANT_CACHE_PREFIX + tenantCode);
        return true;
    }

    @Transactional
    public void decreaseUsedStorage(String tenantCode, long size) {
        Tenant tenant = getTenantByCode(tenantCode);
        tenant.setUsedStorage(Math.max(0, tenant.getUsedStorage() - size));
        tenantRepository.save(tenant);
        redisUtil.delete(TENANT_CACHE_PREFIX + tenantCode);
    }

    public boolean checkStorageQuota(String tenantCode, long fileSize) {
        Tenant tenant = getTenantByCode(tenantCode);
        if (tenant.getStatus() != 1) {
            throw new RuntimeException("租户已被禁用");
        }
        if (tenant.getStorageQuota() <= 0) {
            return true;
        }
        return tenant.getUsedStorage() + fileSize <= tenant.getStorageQuota();
    }
}
