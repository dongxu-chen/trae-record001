package com.configcenter.server.service;

import com.configcenter.server.entity.ConfigAuditLog;
import com.configcenter.server.entity.ConfigSnapshot;
import com.configcenter.server.entity.ConfigVersion;
import com.configcenter.server.repository.ConfigAuditLogRepository;
import com.configcenter.server.repository.ConfigSnapshotRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.servlet.http.HttpServletRequest;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Optional;

@Service
public class ConfigSnapshotService {

    private static final Logger logger = LoggerFactory.getLogger(ConfigSnapshotService.class);

    @Autowired
    private ConfigSnapshotRepository snapshotRepository;

    @Autowired
    private ConfigAuditLogRepository auditLogRepository;

    @Autowired
    private GitService gitService;

    @Autowired
    private BusRefreshService busRefreshService;

    @Transactional
    public ConfigSnapshot createSnapshot(String application, String profile, String label,
                                          String configContent, String description,
                                          String createdBy, String gitCommitId) {
        String version = "snap-" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"));

        ConfigSnapshot snapshot = new ConfigSnapshot();
        snapshot.setApplication(application);
        snapshot.setProfile(profile);
        snapshot.setLabel(label);
        snapshot.setVersion(version);
        snapshot.setConfigContent(configContent);
        snapshot.setDescription(description);
        snapshot.setCreatedBy(createdBy);
        snapshot.setGitCommitId(gitCommitId);

        ConfigSnapshot saved = snapshotRepository.save(snapshot);
        logger.info("配置快照已创建: application={}, version={}", application, version);

        return saved;
    }

    @Transactional
    public ConfigSnapshot restoreToTimePoint(String application, String profile, String label,
                                              LocalDateTime targetTime, String operator,
                                              HttpServletRequest request) {
        logger.info("开始时间点回溯: application={}, targetTime={}", application, targetTime);

        List<ConfigSnapshot> snapshots = snapshotRepository.findLatestSnapshotBeforeTime(
                application, profile, label, targetTime);

        if (snapshots.isEmpty()) {
            throw new RuntimeException("在指定时间点之前没有找到配置快照");
        }

        ConfigSnapshot targetSnapshot = snapshots.get(0);
        logger.info("找到目标快照: version={}, snapshotTime={}",
                targetSnapshot.getVersion(), targetSnapshot.getSnapshotTime());

        String currentConfig = gitService.getConfigContent(application, profile, label);

        String gitCommitId = gitService.commitAndPush(
                application, profile, label,
                targetSnapshot.getConfigContent(),
                "时间点回溯恢复到: " + targetSnapshot.getSnapshotTime());

        targetSnapshot.setGitCommitId(gitCommitId);
        snapshotRepository.save(targetSnapshot);

        busRefreshService.refreshConfig(application);

        saveAuditLog(application, profile, label,
                ConfigAuditLog.ActionType.ROLLBACK,
                currentConfig, targetSnapshot.getConfigContent(),
                null, targetSnapshot.getVersion(),
                operator, getClientIp(request),
                "时间点回溯恢复到: " + targetSnapshot.getSnapshotTime() +
                        ", 快照版本: " + targetSnapshot.getVersion() +
                        ", Git Commit: " + gitCommitId);

        logger.info("时间点回溯恢复完成");
        return targetSnapshot;
    }

    @Transactional
    public ConfigSnapshot restoreToSnapshot(Long snapshotId, String operator,
                                             HttpServletRequest request) {
        ConfigSnapshot snapshot = snapshotRepository.findById(snapshotId)
                .orElseThrow(() -> new RuntimeException("快照不存在: " + snapshotId));

        logger.info("开始恢复到快照: version={}, snapshotTime={}",
                snapshot.getVersion(), snapshot.getSnapshotTime());

        String currentConfig = gitService.getConfigContent(
                snapshot.getApplication(), snapshot.getProfile(), snapshot.getLabel());

        String gitCommitId = gitService.commitAndPush(
                snapshot.getApplication(), snapshot.getProfile(), snapshot.getLabel(),
                snapshot.getConfigContent(),
                "恢复快照: " + snapshot.getVersion());

        snapshot.setGitCommitId(gitCommitId);
        snapshotRepository.save(snapshot);

        busRefreshService.refreshConfig(snapshot.getApplication());

        saveAuditLog(snapshot.getApplication(), snapshot.getProfile(), snapshot.getLabel(),
                ConfigAuditLog.ActionType.ROLLBACK,
                currentConfig, snapshot.getConfigContent(),
                null, snapshot.getVersion(),
                operator, getClientIp(request),
                "恢复快照: " + snapshot.getVersion() +
                        ", 快照时间: " + snapshot.getSnapshotTime() +
                        ", Git Commit: " + gitCommitId);

        logger.info("快照恢复完成");
        return snapshot;
    }

    public List<ConfigSnapshot> getSnapshotHistory(String application) {
        return snapshotRepository.findByApplicationOrderBySnapshotTimeDesc(application);
    }

    public List<ConfigSnapshot> getSnapshots(String application, String profile, String label) {
        return snapshotRepository.findByApplicationAndProfileAndLabelOrderBySnapshotTimeDesc(
                application, profile, label);
    }

    public List<ConfigSnapshot> getSnapshotsInTimeRange(String application, String profile,
                                                         String label, LocalDateTime startTime,
                                                         LocalDateTime endTime) {
        return snapshotRepository.findSnapshotsInTimeRange(
                application, profile, label, startTime, endTime);
    }

    public Optional<ConfigSnapshot> getSnapshot(Long id) {
        return snapshotRepository.findById(id);
    }

    public Optional<ConfigSnapshot> getLatestSnapshot(String application, String profile, String label) {
        List<ConfigSnapshot> snapshots = snapshotRepository
                .findByApplicationAndProfileAndLabelOrderBySnapshotTimeDesc(
                        application, profile, label);
        return snapshots.isEmpty() ? Optional.empty() : Optional.of(snapshots.get(0));
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
