package com.configcenter.server.service;

import com.configcenter.server.entity.ConfigAuditLog;
import com.configcenter.server.entity.GrayRelease;
import com.configcenter.server.repository.ConfigAuditLogRepository;
import com.configcenter.server.repository.GrayReleaseRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.servlet.http.HttpServletRequest;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Service
public class GrayReleaseService {

    @Autowired
    private GrayReleaseRepository grayReleaseRepository;

    @Autowired
    private ConfigAuditLogRepository auditLogRepository;

    @Autowired
    private GitService gitService;

    @Autowired
    private BusRefreshService busRefreshService;

    @Transactional
    public GrayRelease createGrayRelease(String application, String profile, String label,
                                          String configContent, GrayRelease.GrayStrategy strategy,
                                          String grayIps, Integer grayPercentage,
                                          String podLabelSelector,
                                          String createdBy, HttpServletRequest request) {
        Optional<GrayRelease> activeGray = grayReleaseRepository.findActiveGrayRelease(
                application, profile, label);
        if (activeGray.isPresent()) {
            throw new RuntimeException("该配置已有进行中的灰度发布，请先处理完成");
        }

        GrayRelease grayRelease = new GrayRelease();
        grayRelease.setApplication(application);
        grayRelease.setProfile(profile);
        grayRelease.setLabel(label);
        grayRelease.setVersion("gray-" + System.currentTimeMillis());
        grayRelease.setConfigContent(configContent);
        grayRelease.setStrategy(strategy);
        grayRelease.setGrayIps(grayIps);
        grayRelease.setGrayPercentage(grayPercentage);
        grayRelease.setPodLabelSelector(podLabelSelector);
        grayRelease.setCreatedBy(createdBy);
        grayRelease.setStatus(GrayRelease.GrayStatus.PENDING_APPROVAL);

        GrayRelease saved = grayReleaseRepository.save(grayRelease);

        saveAuditLog(application, profile, label,
                ConfigAuditLog.ActionType.GRAY_RELEASE,
                null, configContent, null, grayRelease.getVersion(),
                createdBy, getClientIp(request),
                "创建灰度发布, 策略: " + strategy + ", 版本: " + grayRelease.getVersion());

        return saved;
    }

    @Transactional
    public GrayRelease approveGrayRelease(Long grayReleaseId, String approvedBy,
                                           HttpServletRequest request) {
        GrayRelease grayRelease = grayReleaseRepository.findById(grayReleaseId)
                .orElseThrow(() -> new RuntimeException("灰度发布不存在: " + grayReleaseId));

        if (grayRelease.getStatus() != GrayRelease.GrayStatus.PENDING_APPROVAL) {
            throw new RuntimeException("当前状态不允许审批");
        }

        grayRelease.setStatus(GrayRelease.GrayStatus.IN_GRAY);
        grayRelease.setApprovedBy(approvedBy);
        grayRelease.setApprovedAt(LocalDateTime.now());

        GrayRelease saved = grayReleaseRepository.save(grayRelease);

        busRefreshService.refreshConfig(grayRelease.getApplication());

        saveAuditLog(grayRelease.getApplication(), grayRelease.getProfile(),
                grayRelease.getLabel(),
                ConfigAuditLog.ActionType.GRAY_RELEASE,
                null, grayRelease.getConfigContent(),
                null, grayRelease.getVersion(),
                approvedBy, getClientIp(request),
                "审批通过灰度发布, 版本: " + grayRelease.getVersion());

        return saved;
    }

    @Transactional
    public GrayRelease rejectGrayRelease(Long grayReleaseId, String rejectedBy,
                                          HttpServletRequest request) {
        GrayRelease grayRelease = grayReleaseRepository.findById(grayReleaseId)
                .orElseThrow(() -> new RuntimeException("灰度发布不存在: " + grayReleaseId));

        if (grayRelease.getStatus() != GrayRelease.GrayStatus.PENDING_APPROVAL) {
            throw new RuntimeException("当前状态不允许审批");
        }

        grayRelease.setStatus(GrayRelease.GrayStatus.REJECTED);
        GrayRelease saved = grayReleaseRepository.save(grayRelease);

        saveAuditLog(grayRelease.getApplication(), grayRelease.getProfile(),
                grayRelease.getLabel(),
                ConfigAuditLog.ActionType.GRAY_RELEASE,
                null, null, null, grayRelease.getVersion(),
                rejectedBy, getClientIp(request),
                "拒绝灰度发布, 版本: " + grayRelease.getVersion());

        return saved;
    }

    @Transactional
    public GrayRelease fullRelease(Long grayReleaseId, String operator,
                                    HttpServletRequest request) {
        GrayRelease grayRelease = grayReleaseRepository.findById(grayReleaseId)
                .orElseThrow(() -> new RuntimeException("灰度发布不存在: " + grayReleaseId));

        if (grayRelease.getStatus() != GrayRelease.GrayStatus.IN_GRAY) {
            throw new RuntimeException("当前状态不允许全量发布");
        }

        String currentConfig = gitService.getConfigContent(
                grayRelease.getApplication(), grayRelease.getProfile(), grayRelease.getLabel());

        String gitCommitId = gitService.commitAndPush(
                grayRelease.getApplication(), grayRelease.getProfile(),
                grayRelease.getLabel(), grayRelease.getConfigContent(),
                "灰度全量发布: " + grayRelease.getVersion());

        grayRelease.setStatus(GrayRelease.GrayStatus.FULL_RELEASED);
        grayRelease.setFullReleaseAt(LocalDateTime.now());
        GrayRelease saved = grayReleaseRepository.save(grayRelease);

        busRefreshService.refreshConfig(grayRelease.getApplication());

        saveAuditLog(grayRelease.getApplication(), grayRelease.getProfile(),
                grayRelease.getLabel(),
                ConfigAuditLog.ActionType.PUBLISH,
                currentConfig, grayRelease.getConfigContent(),
                null, grayRelease.getVersion(),
                operator, getClientIp(request),
                "灰度全量发布, 版本: " + grayRelease.getVersion() + ", Git Commit: " + gitCommitId);

        return saved;
    }

    @Transactional
    public GrayRelease rollbackGrayRelease(Long grayReleaseId, String operator,
                                            HttpServletRequest request) {
        GrayRelease grayRelease = grayReleaseRepository.findById(grayReleaseId)
                .orElseThrow(() -> new RuntimeException("灰度发布不存在: " + grayReleaseId));

        if (grayRelease.getStatus() != GrayRelease.GrayStatus.IN_GRAY) {
            throw new RuntimeException("当前状态不允许回滚");
        }

        grayRelease.setStatus(GrayRelease.GrayStatus.ROLLED_BACK);
        GrayRelease saved = grayReleaseRepository.save(grayRelease);

        busRefreshService.refreshConfig(grayRelease.getApplication());

        saveAuditLog(grayRelease.getApplication(), grayRelease.getProfile(),
                grayRelease.getLabel(),
                ConfigAuditLog.ActionType.GRAY_ROLLBACK,
                grayRelease.getConfigContent(), null,
                grayRelease.getVersion(), null,
                operator, getClientIp(request),
                "灰度发布回滚, 版本: " + grayRelease.getVersion());

        return saved;
    }

    public List<GrayRelease> getGrayReleaseHistory(String application) {
        return grayReleaseRepository.findByApplicationOrderByCreatedAtDesc(application);
    }

    public List<GrayRelease> getActiveAndPendingGrayReleases() {
        return grayReleaseRepository.findActiveAndPendingGrayReleases();
    }

    public Optional<GrayRelease> getActiveGrayRelease(String application, String profile, String label) {
        return grayReleaseRepository.findActiveGrayRelease(application, profile, label);
    }

    public Optional<GrayRelease> getGrayRelease(Long id) {
        return grayReleaseRepository.findById(id);
    }

    public boolean isGrayRequest(String application, String profile, String label, String clientIp) {
        return isGrayRequest(application, profile, label, clientIp, null);
    }

    public boolean isGrayRequest(String application, String profile, String label,
                                  String clientIp, java.util.Map<String, String> podLabels) {
        Optional<GrayRelease> activeGray = grayReleaseRepository.findActiveGrayRelease(
                application, profile, label);

        if (!activeGray.isPresent()) {
            return false;
        }

        GrayRelease grayRelease = activeGray.get();

        switch (grayRelease.getStrategy()) {
            case IP_LIST:
                return grayRelease.getGrayIpList().contains(clientIp);
            case PERCENTAGE:
                if (grayRelease.getGrayPercentage() != null && grayRelease.getGrayPercentage() > 0) {
                    int hash = Math.abs(clientIp.hashCode());
                    return (hash % 100) < grayRelease.getGrayPercentage();
                }
                return false;
            case POD_LABEL:
                return matchPodLabels(grayRelease.getPodLabelMap(), podLabels);
            default:
                return false;
        }
    }

    private boolean matchPodLabels(java.util.Map<String, String> selectorLabels,
                                    java.util.Map<String, String> podLabels) {
        if (selectorLabels == null || selectorLabels.isEmpty()) {
            return false;
        }
        if (podLabels == null || podLabels.isEmpty()) {
            return false;
        }

        for (java.util.Map.Entry<String, String> entry : selectorLabels.entrySet()) {
            String podValue = podLabels.get(entry.getKey());
            if (podValue == null || !podValue.equals(entry.getValue())) {
                return false;
            }
        }
        return true;
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
