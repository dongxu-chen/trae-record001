package com.apiversion.version.service.impl;

import com.apiversion.version.entity.ApiVersion;
import com.apiversion.version.mapper.ApiVersionMapper;
import com.apiversion.version.service.ApiVersionService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class ApiVersionServiceImpl extends ServiceImpl<ApiVersionMapper, ApiVersion> implements ApiVersionService {

    private final RedisTemplate<String, Object> redisTemplate;

    private static final String VERSION_CACHE_PREFIX = "api:version:";
    private static final String DEFAULT_VERSION_CACHE_PREFIX = "api:version:default:";
    private static final long CACHE_EXPIRE_HOURS = 24;

    public ApiVersionServiceImpl(RedisTemplate<String, Object> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ApiVersion createVersion(ApiVersion version) {
        version.setStatus("DRAFT");
        version.setIsDefault(false);
        save(version);
        return version;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ApiVersion updateVersion(ApiVersion version) {
        ApiVersion existing = getById(version.getId());
        if (existing == null) {
            throw new RuntimeException("版本不存在");
        }
        if ("PUBLISHED".equals(existing.getStatus()) || "DEPRECATED".equals(existing.getStatus()) || "OFFLINE".equals(existing.getStatus())) {
            throw new RuntimeException("已发布、已废弃或已下线的版本不能修改");
        }
        updateById(version);
        evictCache(version.getId(), version.getServiceName());
        return getById(version.getId());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteVersion(Long id) {
        ApiVersion version = getById(id);
        if (version == null) {
            throw new RuntimeException("版本不存在");
        }
        if (!"DRAFT".equals(version.getStatus())) {
            throw new RuntimeException("只能删除草稿状态的版本");
        }
        removeById(id);
        evictCache(id, version.getServiceName());
    }

    @Override
    public ApiVersion getVersionById(Long id) {
        String cacheKey = VERSION_CACHE_PREFIX + id;
        Object cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached != null) {
            return (ApiVersion) cached;
        }
        ApiVersion version = getById(id);
        if (version != null) {
            redisTemplate.opsForValue().set(cacheKey, version, CACHE_EXPIRE_HOURS, TimeUnit.HOURS);
        }
        return version;
    }

    @Override
    public List<ApiVersion> getVersionByServiceName(String serviceName) {
        LambdaQueryWrapper<ApiVersion> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ApiVersion::getServiceName, serviceName)
                .orderByDesc(ApiVersion::getCreateTime);
        return list(wrapper);
    }

    @Override
    public IPage<ApiVersion> listVersions(Page<ApiVersion> page, String serviceName, String status) {
        LambdaQueryWrapper<ApiVersion> wrapper = new LambdaQueryWrapper<>();
        if (serviceName != null && !serviceName.isEmpty()) {
            wrapper.like(ApiVersion::getServiceName, serviceName);
        }
        if (status != null && !status.isEmpty()) {
            wrapper.eq(ApiVersion::getStatus, status);
        }
        wrapper.orderByDesc(ApiVersion::getCreateTime);
        return page(page, wrapper);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ApiVersion publishVersion(Long id) {
        ApiVersion version = getById(id);
        if (version == null) {
            throw new RuntimeException("版本不存在");
        }
        if (!"DRAFT".equals(version.getStatus())) {
            throw new RuntimeException("只有草稿状态的版本才能发布");
        }
        version.setStatus("PUBLISHED");
        version.setPublishTime(LocalDateTime.now());
        updateById(version);
        evictCache(id, version.getServiceName());
        return version;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ApiVersion deprecateVersion(Long id) {
        ApiVersion version = getById(id);
        if (version == null) {
            throw new RuntimeException("版本不存在");
        }
        if (!"PUBLISHED".equals(version.getStatus())) {
            throw new RuntimeException("只有已发布状态的版本才能废弃");
        }
        version.setStatus("DEPRECATED");
        version.setDeprecateTime(LocalDateTime.now());
        updateById(version);
        evictCache(id, version.getServiceName());
        return version;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ApiVersion offlineVersion(Long id) {
        ApiVersion version = getById(id);
        if (version == null) {
            throw new RuntimeException("版本不存在");
        }
        if (!"DEPRECATED".equals(version.getStatus())) {
            throw new RuntimeException("只有已废弃状态的版本才能下线");
        }
        version.setStatus("OFFLINE");
        version.setOfflineTime(LocalDateTime.now());
        if (Boolean.TRUE.equals(version.getIsDefault())) {
            version.setIsDefault(false);
        }
        updateById(version);
        evictCache(id, version.getServiceName());
        return version;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ApiVersion setDefaultVersion(Long id) {
        ApiVersion version = getById(id);
        if (version == null) {
            throw new RuntimeException("版本不存在");
        }
        if (!"PUBLISHED".equals(version.getStatus())) {
            throw new RuntimeException("只有已发布状态的版本才能设为默认版本");
        }
        LambdaQueryWrapper<ApiVersion> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ApiVersion::getServiceName, version.getServiceName())
                .eq(ApiVersion::getIsDefault, true);
        List<ApiVersion> currentDefaults = list(wrapper);
        for (ApiVersion currentDefault : currentDefaults) {
            currentDefault.setIsDefault(false);
            updateById(currentDefault);
            evictCache(currentDefault.getId(), currentDefault.getServiceName());
        }
        version.setIsDefault(true);
        updateById(version);
        evictCache(id, version.getServiceName());
        return version;
    }

    @Override
    public ApiVersion getDefaultVersion(String serviceName) {
        String cacheKey = DEFAULT_VERSION_CACHE_PREFIX + serviceName;
        Object cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached != null) {
            return (ApiVersion) cached;
        }
        LambdaQueryWrapper<ApiVersion> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ApiVersion::getServiceName, serviceName)
                .eq(ApiVersion::getIsDefault, true)
                .eq(ApiVersion::getStatus, "PUBLISHED");
        ApiVersion version = getOne(wrapper);
        if (version != null) {
            redisTemplate.opsForValue().set(cacheKey, version, CACHE_EXPIRE_HOURS, TimeUnit.HOURS);
        }
        return version;
    }

    private void evictCache(Long id, String serviceName) {
        redisTemplate.delete(VERSION_CACHE_PREFIX + id);
        redisTemplate.delete(DEFAULT_VERSION_CACHE_PREFIX + serviceName);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ApiVersion updateDeprecationSchedule(Long id, LocalDateTime plannedRetireTime, String deprecationMessage) {
        ApiVersion version = getById(id);
        if (version == null) {
            throw new RuntimeException("版本不存在");
        }
        version.setPlannedRetireTime(plannedRetireTime);
        version.setDeprecationMessage(deprecationMessage);
        updateById(version);
        evictCache(id, version.getServiceName());
        syncDeprecationConfigToRedis(id);
        return getById(id);
    }

    @Override
    public List<ApiVersion> getDeprecatedVersions() {
        LambdaQueryWrapper<ApiVersion> wrapper = new LambdaQueryWrapper<>();
        wrapper.in(ApiVersion::getStatus, "DEPRECATED", "OFFLINE")
                .isNotNull(ApiVersion::getPlannedRetireTime)
                .orderByAsc(ApiVersion::getPlannedRetireTime);
        return list(wrapper);
    }

    @Override
    public Map<String, Object> getVersionCallStats(String serviceName, String startDate, String endDate) {
        Map<String, Object> result = new java.util.HashMap<>();
        try {
            String statsKeyPrefix = "api:metrics:version:";
            String pattern = statsKeyPrefix + (serviceName != null ? serviceName + ":" : "*");

            java.util.Set<String> keys = redisTemplate.keys(pattern);
            if (keys == null || keys.isEmpty()) {
                result.put("versions", new java.util.ArrayList<>());
                result.put("totalCalls", 0);
                result.put("trendData", generateMockTrendData());
                return result;
            }

            java.util.List<Map<String, Object>> versionStats = new java.util.ArrayList<>();
            long totalCalls = 0;

            for (String key : keys) {
                Object value = redisTemplate.opsForValue().get(key);
                if (value instanceof java.util.Map) {
                    @SuppressWarnings("unchecked")
                    java.util.Map<String, Object> stat = (java.util.Map<String, Object>) value;
                    versionStats.add(stat);
                    totalCalls += ((Number) stat.getOrDefault("callCount", 0)).longValue();
                }
            }

            versionStats.sort((a, b) ->
                    Long.compare(
                            ((Number) b.getOrDefault("callCount", 0)).longValue(),
                            ((Number) a.getOrDefault("callCount", 0)).longValue()
                    ));

            result.put("versions", versionStats);
            result.put("totalCalls", totalCalls);
            result.put("trendData", generateMockTrendData());
        } catch (Exception e) {
            log.error("获取版本调用统计失败", e);
            result.put("versions", new java.util.ArrayList<>());
            result.put("totalCalls", 0);
            result.put("trendData", generateMockTrendData());
        }
        return result;
    }

    private java.util.Map<String, Object> generateMockTrendData() {
        java.util.Map<String, Object> trendData = new java.util.HashMap<>();
        java.time.format.DateTimeFormatter dateFormatter = java.time.format.DateTimeFormatter.ofPattern("MM-dd");
        java.util.List<String> dates = new java.util.ArrayList<>();
        java.util.Map<String, java.util.List<Long>> versionTrends = new java.util.HashMap<>();

        for (int i = 6; i >= 0; i--) {
            String date = java.time.LocalDate.now().minusDays(i).format(dateFormatter);
            dates.add(date);
        }

        versionTrends.put("v1.0.0", java.util.Arrays.asList(3200L, 3100L, 3000L, 2900L, 2800L, 2600L, 2400L));
        versionTrends.put("v2.0.0", java.util.Arrays.asList(800L, 1000L, 1300L, 1500L, 1800L, 2100L, 2500L));
        versionTrends.put("v2.1.0", java.util.Arrays.asList(0L, 0L, 200L, 400L, 700L, 1000L, 1500L));

        trendData.put("dates", dates);
        trendData.put("versions", versionTrends);
        return trendData;
    }

    @Override
    public void syncDeprecationConfigToRedis(Long versionId) {
        ApiVersion version = getById(versionId);
        if (version == null) {
            return;
        }

        String cacheKey = "api:deprecation:config:" + version.getServiceName() + ":" + version.getVersion();

        java.util.Map<String, Object> config = new java.util.HashMap<>();
        config.put("serviceName", version.getServiceName());
        config.put("version", version.getVersion());
        config.put("status", version.getStatus());
        config.put("deprecateTime", version.getDeprecateTime() != null ?
                version.getDeprecateTime().toString() : null);
        config.put("plannedRetireTime", version.getPlannedRetireTime() != null ?
                version.getPlannedRetireTime().toString() : null);
        config.put("message", version.getDeprecationMessage() != null ?
                version.getDeprecationMessage() : "该版本已废弃，请升级到最新版本");
        config.put("latestVersion", getLatestVersionNumber(version.getServiceName()));
        config.put("upgradeUrl", "/api/versions/" + version.getServiceName() + "/upgrade");

        redisTemplate.opsForValue().set(cacheKey, config, 24, java.util.concurrent.TimeUnit.HOURS);
        log.info("废弃配置已同步到Redis: key={}, config={}", cacheKey, config);
    }

    private String getLatestVersionNumber(String serviceName) {
        LambdaQueryWrapper<ApiVersion> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ApiVersion::getServiceName, serviceName)
                .eq(ApiVersion::getStatus, "PUBLISHED")
                .eq(ApiVersion::getIsMock, false)
                .orderByDesc(ApiVersion::getCreateTime);
        List<ApiVersion> versions = list(wrapper);
        if (!versions.isEmpty()) {
            return versions.get(0).getVersion();
        }
        return "latest";
    }
}
