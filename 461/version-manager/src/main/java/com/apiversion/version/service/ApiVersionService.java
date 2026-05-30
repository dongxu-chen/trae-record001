package com.apiversion.version.service;

import com.apiversion.version.entity.ApiVersion;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import java.util.List;

public interface ApiVersionService {

    ApiVersion createVersion(ApiVersion version);

    ApiVersion updateVersion(ApiVersion version);

    void deleteVersion(Long id);

    ApiVersion getVersionById(Long id);

    List<ApiVersion> getVersionByServiceName(String serviceName);

    IPage<ApiVersion> listVersions(Page<ApiVersion> page, String serviceName, String status);

    ApiVersion publishVersion(Long id);

    ApiVersion deprecateVersion(Long id);

    ApiVersion offlineVersion(Long id);

    ApiVersion setDefaultVersion(Long id);

    ApiVersion getDefaultVersion(String serviceName);

    ApiVersion updateDeprecationSchedule(Long id, java.time.LocalDateTime plannedRetireTime, String deprecationMessage);

    java.util.List<com.apiversion.version.entity.ApiVersion> getDeprecatedVersions();

    java.util.Map<String, Object> getVersionCallStats(String serviceName, String startDate, String endDate);

    void syncDeprecationConfigToRedis(Long versionId);
}
