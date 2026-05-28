package com.configcenter.server.service;

import com.configcenter.server.entity.ConfigVersion;
import com.configcenter.server.entity.ConfigAuditLog;
import com.configcenter.server.repository.ConfigAuditLogRepository;
import com.configcenter.server.repository.ConfigVersionRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.config.server.environment.EnvironmentRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.servlet.http.HttpServletRequest;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Optional;

@Service
public class ConfigVersionService {

    @Autowired
    private ConfigVersionRepository versionRepository;

    @Autowired
    private ConfigAuditLogRepository auditLogRepository;

    @Autowired
    private EnvironmentRepository environmentRepository;

    @Autowired
    private GitService gitService;

    @Autowired
    private BusRefreshService busRefreshService;

    @Transactional
    public ConfigVersion createVersion(String application, String profile, String label,
                                        String configContent, String changeSummary,
                                        String operator, HttpServletRequest request) {
        String version = generateVersion();

        ConfigVersion versionEntity = new ConfigVersion();
        versionEntity.setApplication(application);
        versionEntity.setProfile(profile);
        versionEntity.setLabel(label);
        versionEntity.setVersion(version);
        versionEntity.setConfigContent(configContent);
        versionEntity.setChangeSummary(changeSummary);
        versionEntity.setOperator(operator);
        versionEntity.setStatus(ConfigVersion.VersionStatus.DRAFT);

        ConfigVersion saved = versionRepository.save(versionEntity);

        saveAuditLog(application, profile, label,
                ConfigAuditLog.ActionType.CREATE,
                null, configContent, null, version,
                operator, getClientIp(request), "创建配置版本: " + version);

        return saved;
    }

    @Transactional
    public ConfigVersion publishVersion(Long versionId, String operator,
                                         HttpServletRequest request) {
        ConfigVersion version = versionRepository.findById(versionId)
                .orElseThrow(() -> new RuntimeException("配置版本不存在: " + versionId));

        String oldPublishedConfig = getCurrentPublishedConfig(
                version.getApplication(), version.getProfile(), version.getLabel());

        String gitCommitId = gitService.commitAndPush(
                version.getApplication(), version.getProfile(), version.getLabel(),
                version.getConfigContent(), version.getChangeSummary());

        version.setGitCommitId(gitCommitId);
        version.setGitCommitMessage(version.getChangeSummary());
        version.setStatus(ConfigVersion.VersionStatus.PUBLISHED);
        ConfigVersion saved = versionRepository.save(version);

        busRefreshService.refreshConfig(version.getApplication());

        saveAuditLog(version.getApplication(), version.getProfile(), version.getLabel(),
                ConfigAuditLog.ActionType.PUBLISH,
                oldPublishedConfig, version.getConfigContent(),
                null, version.getVersion(),
                operator, getClientIp(request),
                "发布配置版本: " + version.getVersion() + ", Git Commit: " + gitCommitId);

        return saved;
    }

    @Transactional
    public ConfigVersion rollback(Long versionId, String operator,
                                   HttpServletRequest request) {
        ConfigVersion targetVersion = versionRepository.findById(versionId)
                .orElseThrow(() -> new RuntimeException("配置版本不存在: " + versionId));

        List<ConfigVersion> publishedList = versionRepository.findPublishedVersions(
                targetVersion.getApplication(), targetVersion.getProfile(),
                targetVersion.getLabel());

        if (publishedList.isEmpty()) {
            throw new RuntimeException("没有已发布的版本可回滚");
        }

        ConfigVersion currentPublished = publishedList.get(0);
        String currentConfig = currentPublished.getConfigContent();

        String rollbackVersion = generateVersion();
        ConfigVersion rollbackEntity = new ConfigVersion();
        rollbackEntity.setApplication(targetVersion.getApplication());
        rollbackEntity.setProfile(targetVersion.getProfile());
        rollbackEntity.setLabel(targetVersion.getLabel());
        rollbackEntity.setVersion(rollbackVersion);
        rollbackEntity.setConfigContent(targetVersion.getConfigContent());
        rollbackEntity.setChangeSummary("回滚到版本: " + targetVersion.getVersion());
        rollbackEntity.setOperator(operator);
        rollbackEntity.setStatus(ConfigVersion.VersionStatus.PUBLISHED);
        rollbackEntity.setRolledBackFrom(targetVersion.getId());

        String gitCommitId = gitService.commitAndPush(
                targetVersion.getApplication(), targetVersion.getProfile(),
                targetVersion.getLabel(), targetVersion.getConfigContent(),
                "回滚到版本: " + targetVersion.getVersion());

        rollbackEntity.setGitCommitId(gitCommitId);
        rollbackEntity.setGitCommitMessage("回滚到版本: " + targetVersion.getVersion());

        currentPublished.setStatus(ConfigVersion.VersionStatus.ARCHIVED);
        versionRepository.save(currentPublished);

        ConfigVersion saved = versionRepository.save(rollbackEntity);

        busRefreshService.refreshConfig(targetVersion.getApplication());

        saveAuditLog(targetVersion.getApplication(), targetVersion.getProfile(),
                targetVersion.getLabel(),
                ConfigAuditLog.ActionType.ROLLBACK,
                currentConfig, targetVersion.getConfigContent(),
                currentPublished.getVersion(), rollbackVersion,
                operator, getClientIp(request),
                "回滚到版本: " + targetVersion.getVersion() + ", 新版本: " + rollbackVersion);

        return saved;
    }

    public List<ConfigVersion> getVersionHistory(String application, String profile, String label) {
        return versionRepository.findByApplicationAndProfileAndLabelOrderByCreatedAtDesc(
                application, profile, label);
    }

    public List<ConfigVersion> getPublishedVersions(String application, String profile, String label) {
        return versionRepository.findPublishedVersions(application, profile, label);
    }

    public Optional<ConfigVersion> getVersion(String application, String profile,
                                                String label, String version) {
        return versionRepository.findByApplicationAndProfileAndLabelAndVersion(
                application, profile, label, version);
    }

    public List<ConfigVersion> getVersionsByApplication(String application) {
        return versionRepository.findByApplicationOrderByCreatedAtDesc(application);
    }

    private String generateVersion() {
        return "v" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"));
    }

    private String getCurrentPublishedConfig(String application, String profile, String label) {
        List<ConfigVersion> publishedList = versionRepository.findPublishedVersions(
                application, profile, label);
        return publishedList.isEmpty() ? null : publishedList.get(0).getConfigContent();
    }

    private void saveAuditLog(String application, String profile, String label,
                               ConfigAuditLog.ActionType action,
                               String oldValue, String newValue,
                               String versionBefore, String versionAfter,
                               String operator, String operatorIp, String remark) {
        ConfigAuditLog auditLog = new ConfigAuditLog();
        auditLog.setApplication(application);
        auditLog.setProfile(profile);
        auditLog.setLabel(label);
        auditLog.setAction(action);
        auditLog.setOldValue(oldValue);
        auditLog.setNewValue(newValue);
        auditLog.setVersionBefore(versionBefore);
        auditLog.setVersionAfter(versionAfter);
        auditLog.setOperator(operator);
        auditLog.setOperatorIp(operatorIp);
        auditLog.setRemark(remark);
        auditLogRepository.save(auditLog);
    }

    private String getClientIp(HttpServletRequest request) {
        if (request == null) {
            return "unknown";
        }
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("X-Real-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        return ip;
    }
}
