package com.apiversion.version.service.impl;

import com.apiversion.version.entity.ApiVersion;
import com.apiversion.version.entity.MockVersionConfig;
import com.apiversion.version.mapper.ApiVersionMapper;
import com.apiversion.version.mapper.MockVersionConfigMapper;
import com.apiversion.version.service.MockVersionService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class MockVersionServiceImpl extends ServiceImpl<MockVersionConfigMapper, MockVersionConfig> implements MockVersionService {

    private final RedisTemplate<String, Object> redisTemplate;
    private final ApiVersionMapper apiVersionMapper;
    private final ObjectMapper objectMapper;

    private static final String MOCK_CONFIG_CACHE_PREFIX = "api:mock:config:";
    private static final long CACHE_EXPIRE_HOURS = 24;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public MockVersionConfig createMockConfig(MockVersionConfig config) {
        ApiVersion version = apiVersionMapper.selectById(config.getVersionId());
        if (version == null) {
            throw new RuntimeException("版本不存在");
        }
        if (config.getEnabled() == null) {
            config.setEnabled(true);
        }
        if (config.getDelayMs() == null) {
            config.setDelayMs(0);
        }
        if (config.getErrorCode() == null) {
            config.setErrorCode(200);
        }
        save(config);
        syncMockConfigToRedis(config.getId());
        return getById(config.getId());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public MockVersionConfig updateMockConfig(MockVersionConfig config) {
        MockVersionConfig existing = getById(config.getId());
        if (existing == null) {
            throw new RuntimeException("Mock配置不存在");
        }
        updateById(config);
        syncMockConfigToRedis(config.getId());
        return getById(config.getId());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteMockConfig(Long id) {
        MockVersionConfig config = getById(id);
        if (config == null) {
            throw new RuntimeException("Mock配置不存在");
        }
        removeById(id);
        evictCache(config);
    }

    @Override
    public MockVersionConfig getMockConfigById(Long id) {
        String cacheKey = MOCK_CONFIG_CACHE_PREFIX + "id:" + id;
        Object cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached != null) {
            try {
                return objectMapper.convertValue(cached, MockVersionConfig.class);
            } catch (Exception e) {
                log.warn("反序列化Mock配置缓存失败: {}", e.getMessage());
            }
        }
        MockVersionConfig config = getById(id);
        if (config != null) {
            redisTemplate.opsForValue().set(cacheKey, config, CACHE_EXPIRE_HOURS, TimeUnit.HOURS);
        }
        return config;
    }

    @Override
    public List<MockVersionConfig> getMockConfigsByVersionId(Long versionId) {
        LambdaQueryWrapper<MockVersionConfig> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(MockVersionConfig::getVersionId, versionId)
                .orderByAsc(MockVersionConfig::getPath);
        return list(wrapper);
    }

    @Override
    public List<MockVersionConfig> getMockConfigsByPath(String path) {
        LambdaQueryWrapper<MockVersionConfig> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(MockVersionConfig::getPath, path)
                .eq(MockVersionConfig::getEnabled, true);
        return list(wrapper);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public MockVersionConfig toggleMockConfig(Long id, boolean enabled) {
        MockVersionConfig config = getById(id);
        if (config == null) {
            throw new RuntimeException("Mock配置不存在");
        }
        config.setEnabled(enabled);
        updateById(config);
        syncMockConfigToRedis(id);
        return config;
    }

    @Override
    public void syncMockConfigToRedis(Long configId) {
        MockVersionConfig config = getById(configId);
        if (config == null || !Boolean.TRUE.equals(config.getEnabled())) {
            return;
        }

        ApiVersion version = apiVersionMapper.selectById(config.getVersionId());
        if (version == null) {
            return;
        }

        Map<String, Object> mockData = new HashMap<>();
        mockData.put("id", config.getId());
        mockData.put("versionId", config.getVersionId());
        mockData.put("serviceName", version.getServiceName());
        mockData.put("apiVersion", version.getVersion());
        mockData.put("path", config.getPath());
        mockData.put("method", config.getMethod());
        mockData.put("mockType", config.getMockType());
        mockData.put("delayMs", config.getDelayMs());
        mockData.put("errorCode", config.getErrorCode());
        mockData.put("errorMessage", config.getErrorMessage());
        mockData.put("customResponse", config.getCustomResponse());

        String pathKey = MOCK_CONFIG_CACHE_PREFIX + "path:" + config.getMethod() + ":" + config.getPath();
        redisTemplate.opsForValue().set(pathKey, mockData, CACHE_EXPIRE_HOURS, TimeUnit.HOURS);

        String versionKey = MOCK_CONFIG_CACHE_PREFIX + "version:" + version.getServiceName() + ":" + version.getVersion() + ":" + config.getMethod() + ":" + config.getPath();
        redisTemplate.opsForValue().set(versionKey, mockData, CACHE_EXPIRE_HOURS, TimeUnit.HOURS);

        String idKey = MOCK_CONFIG_CACHE_PREFIX + "id:" + config.getId();
        redisTemplate.opsForValue().set(idKey, config, CACHE_EXPIRE_HOURS, TimeUnit.HOURS);

        log.info("Mock配置已同步到Redis: path={}, method={}, type={}",
                config.getPath(), config.getMethod(), config.getMockType());
    }

    @Override
    public List<MockVersionConfig> getAllEnabledMockConfigs() {
        LambdaQueryWrapper<MockVersionConfig> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(MockVersionConfig::getEnabled, true)
                .orderByAsc(MockVersionConfig::getPath);
        return list(wrapper);
    }

    private void evictCache(MockVersionConfig config) {
        redisTemplate.delete(MOCK_CONFIG_CACHE_PREFIX + "id:" + config.getId());
        redisTemplate.delete(MOCK_CONFIG_CACHE_PREFIX + "path:" + config.getMethod() + ":" + config.getPath());

        ApiVersion version = apiVersionMapper.selectById(config.getVersionId());
        if (version != null) {
            redisTemplate.delete(MOCK_CONFIG_CACHE_PREFIX + "version:" + version.getServiceName() + ":" + version.getVersion() + ":" + config.getMethod() + ":" + config.getPath());
        }
    }
}
