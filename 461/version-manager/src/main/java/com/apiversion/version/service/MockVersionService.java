package com.apiversion.version.service;

import com.apiversion.version.entity.MockVersionConfig;

import java.util.List;

public interface MockVersionService {

    MockVersionConfig createMockConfig(MockVersionConfig config);

    MockVersionConfig updateMockConfig(MockVersionConfig config);

    void deleteMockConfig(Long id);

    MockVersionConfig getMockConfigById(Long id);

    List<MockVersionConfig> getMockConfigsByVersionId(Long versionId);

    List<MockVersionConfig> getMockConfigsByPath(String path);

    MockVersionConfig toggleMockConfig(Long id, boolean enabled);

    void syncMockConfigToRedis(Long configId);

    List<MockVersionConfig> getAllEnabledMockConfigs();
}
