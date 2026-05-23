package com.configcenter.controller;

import com.configcenter.dto.ConfigDTO;
import com.configcenter.dto.ConfigVersionDTO;
import com.configcenter.dto.GrayReleaseDTO;
import com.configcenter.dto.Result;
import com.configcenter.service.*;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

@RestController
@RequestMapping("/api/config")
public class ConfigController {

    private final GitConfigService gitConfigService;
    private final ConfigValidationService validationService;
    private final LongPollingService longPollingService;
    private final ConfigChangeNotifier changeNotifier;
    private final ConfigDiffService diffService;
    private final GrayReleaseService grayReleaseService;
    private final ConfigSyncService syncService;
    private final ConfigAuditService auditService;

    private final Map<String, RollbackRequest> pendingRollbacks = new ConcurrentHashMap<>();
    private static final long ROLLBACK_TOKEN_EXPIRE_MINUTES = 5;

    public ConfigController(GitConfigService gitConfigService,
                            ConfigValidationService validationService,
                            LongPollingService longPollingService,
                            ConfigChangeNotifier changeNotifier,
                            ConfigDiffService diffService,
                            GrayReleaseService grayReleaseService,
                            ConfigSyncService syncService,
                            ConfigAuditService auditService) {
        this.gitConfigService = gitConfigService;
        this.validationService = validationService;
        this.longPollingService = longPollingService;
        this.changeNotifier = changeNotifier;
        this.diffService = diffService;
        this.grayReleaseService = grayReleaseService;
        this.syncService = syncService;
        this.auditService = auditService;
    }

    @PostMapping("/publish")
    public Result<ConfigDTO> publishConfig(@RequestBody ConfigDTO configDTO) {
        try {
            ConfigValidationService.ValidationResult validationResult =
                    validationService.validate(configDTO.getContent(), configDTO.getFormat());

            if (!validationResult.isValid()) {
                return Result.error(400, "配置格式校验失败: " + String.join("; ", validationResult.getErrors()));
            }

            ConfigDTO result = gitConfigService.publishConfig(configDTO);

            changeNotifier.notifyChange(result.getApplication(), result.getProfile(), result.getVersion());

            return Result.success(result);
        } catch (Exception e) {
            return Result.error("配置发布失败: " + e.getMessage());
        }
    }

    @GetMapping("/{application}/{profile}")
    public Result<ConfigDTO> getConfig(@PathVariable String application,
                                       @PathVariable String profile,
                                       @RequestParam(required = false) String label,
                                       @RequestHeader(value = "X-Instance-Id", required = false) String instanceId,
                                       @RequestHeader(value = "X-Client-Ip", required = false) String clientIpHeader,
                                       HttpServletRequest request) {
        try {
            String clientIp = clientIpHeader != null ? clientIpHeader : request.getRemoteAddr();
            String clientHost = request.getRemoteHost();
            String actualInstanceId = instanceId != null ? instanceId : UUID.randomUUID().toString();

            GrayReleaseDTO grayRelease = grayReleaseService.getGrayRelease(application, profile, clientIp);
            ConfigDTO config;

            if (grayRelease != null) {
                config = new ConfigDTO();
                config.setApplication(application);
                config.setProfile(profile);
                config.setLabel(label);
                config.setContent(grayRelease.getContent());
                config.setFormat(grayRelease.getFormat());
                config.setVersion(grayRelease.getGrayVersion());
                config.setDescription("Gray release config - " + grayRelease.getDescription());
            } else {
                config = gitConfigService.getConfig(application, profile, label);
                if (config == null) {
                    return Result.error(404, "配置不存在");
                }
            }

            auditService.recordConfigAccess(application, profile, config.getVersion(),
                    actualInstanceId, clientIp, clientHost);

            return Result.success(config);
        } catch (Exception e) {
            return Result.error("获取配置失败: " + e.getMessage());
        }
    }

    @GetMapping("/{application}/{profile}/versions")
    public Result<List<ConfigVersionDTO>> getVersionHistory(@PathVariable String application,
                                                            @PathVariable String profile) {
        try {
            List<ConfigVersionDTO> versions = gitConfigService.getVersionHistory(application, profile);
            return Result.success(versions);
        } catch (Exception e) {
            return Result.error("获取版本历史失败: " + e.getMessage());
        }
    }

    @GetMapping("/{application}/{profile}/versions/{version}")
    public Result<String> getConfigByVersion(@PathVariable String application,
                                             @PathVariable String profile,
                                             @PathVariable String version) {
        try {
            String content = gitConfigService.getConfigContentByVersion(application, profile, version);
            if (content == null) {
                return Result.error(404, "版本不存在");
            }
            return Result.success(content);
        } catch (Exception e) {
            return Result.error("获取版本配置失败: " + e.getMessage());
        }
    }

    @PostMapping("/{application}/{profile}/rollback/preview/{version}")
    public Result<Map<String, Object>> previewRollback(@PathVariable String application,
                                                       @PathVariable String profile,
                                                       @PathVariable String version) {
        try {
            ConfigDTO currentConfig = gitConfigService.getConfig(application, profile, null);
            String targetContent = gitConfigService.getConfigContentByVersion(application, profile, version);

            if (currentConfig == null) {
                return Result.error(404, "当前配置不存在");
            }
            if (targetContent == null) {
                return Result.error(404, "目标版本配置不存在");
            }

            ConfigDiffService.DiffResult diffResult = diffService.compareConfigs(
                    currentConfig.getContent(), targetContent, currentConfig.getFormat());
            diffResult.setHighlightedDiff(diffService.generateHighlightedDiff(diffResult));

            String token = UUID.randomUUID().toString();
            pendingRollbacks.put(token, new RollbackRequest(application, profile, version,
                    System.currentTimeMillis() + TimeUnit.MINUTES.toMillis(ROLLBACK_TOKEN_EXPIRE_MINUTES)));

            Map<String, Object> result = Map.of(
                    "token", token,
                    "tokenExpireMinutes", ROLLBACK_TOKEN_EXPIRE_MINUTES,
                    "currentVersion", currentConfig.getVersion(),
                    "targetVersion", version,
                    "diff", diffResult
            );

            return Result.success(result);
        } catch (Exception e) {
            return Result.error("回滚预览失败: " + e.getMessage());
        }
    }

    @PostMapping("/{application}/{profile}/rollback/confirm")
    public Result<ConfigDTO> confirmRollback(@PathVariable String application,
                                             @PathVariable String profile,
                                             @RequestBody Map<String, String> request) {
        String token = request.get("token");
        String operator = request.get("operator");

        if (token == null || token.trim().isEmpty()) {
            return Result.error(400, "回滚令牌不能为空");
        }

        RollbackRequest rollbackRequest = pendingRollbacks.get(token);
        if (rollbackRequest == null) {
            return Result.error(400, "无效的回滚令牌或令牌已过期");
        }

        if (System.currentTimeMillis() > rollbackRequest.getExpireTime()) {
            pendingRollbacks.remove(token);
            return Result.error(400, "回滚令牌已过期，请重新预览");
        }

        if (!rollbackRequest.getApplication().equals(application) ||
                !rollbackRequest.getProfile().equals(profile)) {
            return Result.error(400, "回滚令牌与目标配置不匹配");
        }

        try {
            ConfigDTO result = gitConfigService.rollbackToVersion(
                    rollbackRequest.getApplication(),
                    rollbackRequest.getProfile(),
                    rollbackRequest.getTargetVersion()
            );

            if (operator != null && !operator.isEmpty()) {
                result.setCreatedBy(operator);
            }

            changeNotifier.notifyChange(result.getApplication(), result.getProfile(), result.getVersion());

            pendingRollbacks.remove(token);

            return Result.success(result);
        } catch (Exception e) {
            return Result.error("回滚失败: " + e.getMessage());
        }
    }

    @PostMapping("/{application}/{profile}/rollback/{version}")
    public Result<ConfigDTO> rollbackConfig(@PathVariable String application,
                                            @PathVariable String profile,
                                            @PathVariable String version) {
        return Result.error(400, "请先调用 /rollback/preview/{version} 进行预览，获取token后调用 /rollback/confirm 确认回滚");
    }

    @PostMapping("/diff")
    public Result<ConfigDiffService.DiffResult> diffConfigs(@RequestBody Map<String, String> request) {
        String oldContent = request.get("oldContent");
        String newContent = request.get("newContent");
        String format = request.getOrDefault("format", "yml");

        ConfigDiffService.DiffResult diffResult = diffService.compareConfigs(oldContent, newContent, format);
        diffResult.setHighlightedDiff(diffService.generateHighlightedDiff(diffResult));

        return Result.success(diffResult);
    }

    @GetMapping("/{application}/{profile}/listen")
    public void listenConfig(@PathVariable String application,
                             @PathVariable String profile,
                             @RequestParam(required = false) String currentVersion,
                             HttpServletRequest request,
                             HttpServletResponse response) {
        try {
            if (currentVersion == null) {
                ConfigDTO config = gitConfigService.getConfig(application, profile, null);
                if (config != null) {
                    response.setContentType("application/json;charset=UTF-8");
                    response.getWriter().write("{\"changed\":true,\"newVersion\":\"" + config.getVersion() + "\"}");
                    response.getWriter().flush();
                    return;
                }
            }
            longPollingService.addPollingRequest(application, profile, currentVersion, request, response);
        } catch (Exception e) {
            try {
                response.setStatus(500);
                response.getWriter().write("{\"error\":\"" + e.getMessage() + "\"}");
            } catch (Exception ex) {
            }
        }
    }

    @PostMapping("/validate")
    public Result<Map<String, Object>> validateConfig(@RequestBody Map<String, String> request) {
        String content = request.get("content");
        String format = request.get("format");

        ConfigValidationService.ValidationResult result = validationService.validate(content, format);

        if (result.isValid()) {
            return Result.success(Map.of("valid", true));
        } else {
            return Result.success(Map.of("valid", false, "errors", result.getErrors()));
        }
    }

    @PostMapping("/convert")
    public Result<Map<String, String>> convertConfig(@RequestBody Map<String, String> request) {
        try {
            String content = request.get("content");
            String fromFormat = request.get("from");
            String toFormat = request.get("to");

            String result;
            if ("yaml".equalsIgnoreCase(fromFormat) && "json".equalsIgnoreCase(toFormat)) {
                result = validationService.convertToJson(content);
            } else if ("json".equalsIgnoreCase(fromFormat) && "yaml".equalsIgnoreCase(toFormat)) {
                result = validationService.convertToYaml(content);
            } else {
                return Result.error("不支持的转换格式");
            }

            return Result.success(Map.of("content", result));
        } catch (Exception e) {
            return Result.error("转换失败: " + e.getMessage());
        }
    }

    @PostMapping("/gray/create")
    public Result<GrayReleaseDTO> createGrayRelease(@RequestBody GrayReleaseDTO request) {
        try {
            ConfigValidationService.ValidationResult validationResult =
                    validationService.validate(request.getContent(), request.getFormat());

            if (!validationResult.isValid()) {
                return Result.error(400, "配置格式校验失败: " + String.join("; ", validationResult.getErrors()));
            }

            GrayReleaseDTO result = grayReleaseService.createGrayRelease(request);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error("创建灰度发布失败: " + e.getMessage());
        }
    }

    @GetMapping("/gray/list")
    public Result<List<GrayReleaseDTO>> listGrayReleases(
            @RequestParam(required = false) String application,
            @RequestParam(required = false) String profile) {
        try {
            List<GrayReleaseDTO> result = grayReleaseService.listGrayReleases(application, profile);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error("获取灰度发布列表失败: " + e.getMessage());
        }
    }

    @GetMapping("/gray/{id}")
    public Result<GrayReleaseDTO> getGrayRelease(@PathVariable String id) {
        try {
            GrayReleaseDTO result = grayReleaseService.getGrayReleaseById(id);
            if (result == null) {
                return Result.error(404, "灰度发布不存在");
            }
            return Result.success(result);
        } catch (Exception e) {
            return Result.error("获取灰度发布失败: " + e.getMessage());
        }
    }

    @GetMapping("/gray/{id}/stats")
    public Result<Map<String, Object>> getGrayReleaseStats(@PathVariable String id) {
        try {
            Map<String, Object> result = grayReleaseService.getGrayReleaseStats(id);
            if (result == null) {
                return Result.error(404, "灰度发布不存在");
            }
            return Result.success(result);
        } catch (Exception e) {
            return Result.error("获取灰度发布统计失败: " + e.getMessage());
        }
    }

    @PostMapping("/gray/{id}/update")
    public Result<GrayReleaseDTO> updateGrayRelease(@PathVariable String id, @RequestBody GrayReleaseDTO request) {
        try {
            GrayReleaseDTO result = grayReleaseService.updateGrayRelease(id, request);
            if (result == null) {
                return Result.error(404, "灰度发布不存在");
            }
            return Result.success(result);
        } catch (Exception e) {
            return Result.error("更新灰度发布失败: " + e.getMessage());
        }
    }

    @PostMapping("/gray/{id}/stop")
    public Result<Boolean> stopGrayRelease(@PathVariable String id) {
        try {
            boolean result = grayReleaseService.stopGrayRelease(id);
            if (!result) {
                return Result.error(404, "灰度发布不存在");
            }
            return Result.success(true);
        } catch (Exception e) {
            return Result.error("停止灰度发布失败: " + e.getMessage());
        }
    }

    @PostMapping("/gray/{id}/full")
    public Result<GrayReleaseDTO> fullGrayRelease(@PathVariable String id) {
        try {
            GrayReleaseDTO result = grayReleaseService.fullGrayRelease(id);
            if (result == null) {
                return Result.error(404, "灰度发布不存在");
            }
            return Result.success(result);
        } catch (Exception e) {
            return Result.error("全量发布失败: " + e.getMessage());
        }
    }

    @DeleteMapping("/gray/{id}")
    public Result<Boolean> deleteGrayRelease(@PathVariable String id) {
        try {
            boolean result = grayReleaseService.deleteGrayRelease(id);
            if (!result) {
                return Result.error(404, "灰度发布不存在");
            }
            return Result.success(true);
        } catch (Exception e) {
            return Result.error("删除灰度发布失败: " + e.getMessage());
        }
    }

    @PostMapping("/sync/preview")
    public Result<ConfigSyncService.PreviewResult> previewSync(@RequestBody Map<String, Object> request) {
        try {
            String application = (String) request.get("application");
            String sourceProfile = (String) request.get("sourceProfile");
            String targetProfile = (String) request.get("targetProfile");
            @SuppressWarnings("unchecked")
            Map<String, String> placeholderValues = (Map<String, String>) request.get("placeholderValues");

            ConfigSyncService.PreviewResult result = syncService.previewSync(application, sourceProfile, targetProfile, placeholderValues);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error("同步预览失败: " + e.getMessage());
        }
    }

    @PostMapping("/sync/execute")
    public Result<ConfigSyncService.SyncResult> executeSync(@RequestBody Map<String, Object> request) {
        try {
            String application = (String) request.get("application");
            String sourceProfile = (String) request.get("sourceProfile");
            String targetProfile = (String) request.get("targetProfile");
            @SuppressWarnings("unchecked")
            Map<String, String> placeholderValues = (Map<String, String>) request.get("placeholderValues");
            String operator = (String) request.get("operator");

            ConfigSyncService.SyncResult result = syncService.syncConfig(
                    application, sourceProfile, targetProfile, placeholderValues, operator);

            if (result.isSuccess()) {
                ConfigDTO targetConfig = gitConfigService.getConfig(application, targetProfile, null);
                if (targetConfig != null) {
                    changeNotifier.notifyChange(application, targetProfile, targetConfig.getVersion());
                }
            }

            return Result.success(result);
        } catch (Exception e) {
            return Result.error("同步执行失败: " + e.getMessage());
        }
    }

    @PostMapping("/sync/batch")
    public Result<ConfigSyncService.BatchSyncResult> batchSync(@RequestBody Map<String, Object> request) {
        try {
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> syncRequests = (List<Map<String, Object>>) request.get("syncs");
            String operator = (String) request.get("operator");

            List<ConfigSyncService.SyncRequest> syncRequestList = new java.util.ArrayList<>();
            for (Map<String, Object> syncMap : syncRequests) {
                ConfigSyncService.SyncRequest syncRequest = new ConfigSyncService.SyncRequest();
                syncRequest.setApplication((String) syncMap.get("application"));
                syncRequest.setSourceProfile((String) syncMap.get("sourceProfile"));
                syncRequest.setTargetProfile((String) syncMap.get("targetProfile"));
                @SuppressWarnings("unchecked")
                Map<String, String> placeholders = (Map<String, String>) syncMap.get("placeholderValues");
                syncRequest.setPlaceholderValues(placeholders);
                syncRequestList.add(syncRequest);
            }

            ConfigSyncService.BatchSyncResult result = syncService.batchSyncConfigs(syncRequestList, operator);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error("批量同步失败: " + e.getMessage());
        }
    }

    @GetMapping("/audit/summary")
    public Result<Map<String, Object>> getAuditSummary(
            @RequestParam String application,
            @RequestParam String profile) {
        try {
            Map<String, Object> result = auditService.getConfigAuditSummary(application, profile);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error("获取审计摘要失败: " + e.getMessage());
        }
    }

    @GetMapping("/audit/instances")
    public Result<List<ConfigAuditService.InstanceInfo>> getActiveInstances(
            @RequestParam(required = false) String application,
            @RequestParam(required = false) String profile) {
        try {
            List<ConfigAuditService.InstanceInfo> result = auditService.getActiveInstances(application, profile);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error("获取活跃实例失败: " + e.getMessage());
        }
    }

    @GetMapping("/audit/instances/{instanceId}")
    public Result<Map<String, Object>> getInstanceDetail(@PathVariable String instanceId) {
        try {
            Map<String, Object> result = auditService.getInstanceDetail(instanceId);
            if (result == null) {
                return Result.error(404, "实例不存在");
            }
            return Result.success(result);
        } catch (Exception e) {
            return Result.error("获取实例详情失败: " + e.getMessage());
        }
    }

    @GetMapping("/audit/access")
    public Result<List<ConfigAuditService.ConfigAccessRecord>> getAccessRecords(
            @RequestParam(required = false) String application,
            @RequestParam(required = false) String profile) {
        try {
            List<ConfigAuditService.ConfigAccessRecord> result = auditService.getAccessRecords(application, profile);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error("获取访问记录失败: " + e.getMessage());
        }
    }

    @GetMapping("/audit/usage")
    public Result<List<ConfigAuditService.ConfigUsageStats>> getUsageStats(
            @RequestParam(required = false) String application,
            @RequestParam(required = false) String profile) {
        try {
            List<ConfigAuditService.ConfigUsageStats> result = auditService.getUsageStats(application, profile);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error("获取使用统计失败: " + e.getMessage());
        }
    }

    private static class RollbackRequest {
        private final String application;
        private final String profile;
        private final String targetVersion;
        private final long expireTime;

        public RollbackRequest(String application, String profile, String targetVersion, long expireTime) {
            this.application = application;
            this.profile = profile;
            this.targetVersion = targetVersion;
            this.expireTime = expireTime;
        }

        public String getApplication() { return application; }
        public String getProfile() { return profile; }
        public String getTargetVersion() { return targetVersion; }
        public long getExpireTime() { return expireTime; }
    }
}
