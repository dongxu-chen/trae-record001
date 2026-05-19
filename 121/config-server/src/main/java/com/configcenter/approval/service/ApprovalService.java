package com.configcenter.approval.service;

import com.configcenter.approval.entity.ConfigApproval;
import com.configcenter.approval.repository.ApprovalRepository;
import com.configcenter.audit.entity.ConfigAuditLog;
import com.configcenter.audit.service.AuditService;
import com.configcenter.diff.entity.ConfigDiff;
import com.configcenter.diff.service.DiffService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class ApprovalService {

    private static final Logger logger = LoggerFactory.getLogger(ApprovalService.class);

    @Autowired
    private ApprovalRepository approvalRepository;

    @Autowired
    private DiffService diffService;

    @Autowired
    private AuditService auditService;

    public ConfigApproval createRequest(String serviceName, String profile, String label,
                                         Map<String, Object> targetConfig, String requestedBy,
                                         String changeReason) {
        ConfigApproval approval = new ConfigApproval();
        approval.setId("APP-" + System.currentTimeMillis());
        approval.setServiceName(serviceName);
        approval.setProfile(profile);
        approval.setLabel(label);
        approval.setTargetConfig(targetConfig);
        approval.setRequestedBy(requestedBy);
        approval.setRequestedAt(LocalDateTime.now());
        approval.setChangeReason(changeReason);
        approval.setStatus(ConfigApproval.ApprovalStatus.PENDING);
        approval.setCurrentLevel(ConfigApproval.ApprovalLevel.LEVEL1);
        approval.setApprovalHistory(new ArrayList<>());

        ConfigDiff diff = diffService.compareWithCurrent(serviceName, profile, label, targetConfig);
        approval.setDiffSummary(diffService.generateDiffSummary(diff));

        approvalRepository.save(approval.getId(), approval);
        logger.info("Created approval request: {} for service: {}", approval.getId(), serviceName);
        return approval;
    }

    public ConfigApproval approve(String approvalId, String approver, String comment,
                                   ConfigApproval.ApprovalLevel level) {
        ConfigApproval approval = approvalRepository.findById(approvalId)
                .orElseThrow(() -> new RuntimeException("Approval request not found: " + approvalId));

        if (approval.getStatus() != ConfigApproval.ApprovalStatus.PENDING &&
                approval.getStatus() != ConfigApproval.ApprovalStatus.IN_PROGRESS) {
            throw new RuntimeException("Approval request is not in pending/in-progress state");
        }

        if (approval.getCurrentLevel() != level) {
            throw new RuntimeException("Expected approval at level: " + approval.getCurrentLevel());
        }

        ConfigApproval.ApprovalRecord record = new ConfigApproval.ApprovalRecord();
        record.setLevel(level);
        record.setApprover(approver);
        record.setAction(ConfigApproval.ApprovalRecord.ApprovalAction.APPROVE);
        record.setComment(comment);
        record.setApprovedAt(LocalDateTime.now());
        approval.getApprovalHistory().add(record);

        ConfigApproval.ApprovalLevel nextLevel = level.next();
        if (nextLevel == null) {
            approval.setStatus(ConfigApproval.ApprovalStatus.APPROVED);
            approval.setCurrentLevel(null);
            logger.info("Approval request fully approved: {}", approvalId);
        } else {
            approval.setStatus(ConfigApproval.ApprovalStatus.IN_PROGRESS);
            approval.setCurrentLevel(nextLevel);
            logger.info("Approval request approved at level {}, moving to next level: {}", level, nextLevel);
        }

        approvalRepository.save(approvalId, approval);
        return approval;
    }

    public ConfigApproval reject(String approvalId, String approver, String comment,
                                  ConfigApproval.ApprovalLevel level) {
        ConfigApproval approval = approvalRepository.findById(approvalId)
                .orElseThrow(() -> new RuntimeException("Approval request not found: " + approvalId));

        ConfigApproval.ApprovalRecord record = new ConfigApproval.ApprovalRecord();
        record.setLevel(level);
        record.setApprover(approver);
        record.setAction(ConfigApproval.ApprovalRecord.ApprovalAction.REJECT);
        record.setComment(comment);
        record.setApprovedAt(LocalDateTime.now());
        approval.getApprovalHistory().add(record);
        approval.setStatus(ConfigApproval.ApprovalStatus.REJECTED);

        approvalRepository.save(approvalId, approval);
        logger.info("Approval request rejected: {} by {}", approvalId, approver);
        return approval;
    }

    public ConfigApproval requestChange(String approvalId, String approver, String comment,
                                         ConfigApproval.ApprovalLevel level) {
        ConfigApproval approval = approvalRepository.findById(approvalId)
                .orElseThrow(() -> new RuntimeException("Approval request not found: " + approvalId));

        ConfigApproval.ApprovalRecord record = new ConfigApproval.ApprovalRecord();
        record.setLevel(level);
        record.setApprover(approver);
        record.setAction(ConfigApproval.ApprovalRecord.ApprovalAction.REQUEST_CHANGE);
        record.setComment(comment);
        record.setApprovedAt(LocalDateTime.now());
        approval.getApprovalHistory().add(record);

        approvalRepository.save(approvalId, approval);
        logger.info("Change requested for approval: {} by {}", approvalId, approver);
        return approval;
    }

    public ConfigApproval cancel(String approvalId, String cancelledBy) {
        ConfigApproval approval = approvalRepository.findById(approvalId)
                .orElseThrow(() -> new RuntimeException("Approval request not found: " + approvalId));

        approval.setStatus(ConfigApproval.ApprovalStatus.CANCELLED);
        approvalRepository.save(approvalId, approval);
        logger.info("Approval request cancelled: {} by {}", approvalId, cancelledBy);
        return approval;
    }

    public ConfigAuditLog publishApprovedConfig(String approvalId, String publishedBy) {
        ConfigApproval approval = approvalRepository.findById(approvalId)
                .orElseThrow(() -> new RuntimeException("Approval request not found: " + approvalId));

        if (approval.getStatus() != ConfigApproval.ApprovalStatus.APPROVED) {
            throw new RuntimeException("Approval request is not fully approved");
        }

        Map<String, Object> currentConfig = diffService.fetchCurrentConfig(
                approval.getServiceName(), approval.getProfile(), approval.getLabel());

        ConfigAuditLog auditLog = auditService.logChange(
                ConfigAuditLog.ChangeType.UPDATE,
                approval.getServiceName(),
                approval.getProfile(),
                approval.getLabel(),
                currentConfig,
                approval.getTargetConfig(),
                publishedBy,
                "Published via approval: " + approvalId + ". Reason: " + approval.getChangeReason()
        );

        approval.setStatus(ConfigApproval.ApprovalStatus.PUBLISHED);
        approvalRepository.save(approvalId, approval);

        logger.info("Published approved config for approval: {} by {}", approvalId, publishedBy);
        return auditLog;
    }

    public Optional<ConfigApproval> getApproval(String id) {
        return approvalRepository.findById(id);
    }

    public List<ConfigApproval> getAllApprovals() {
        return approvalRepository.findAll();
    }

    public List<ConfigApproval> getApprovalsByService(String serviceName) {
        return approvalRepository.findByServiceName(serviceName);
    }

    public List<ConfigApproval> getApprovalsByStatus(ConfigApproval.ApprovalStatus status) {
        return approvalRepository.findByStatus(status);
    }

    public List<ConfigApproval> getApprovalsByRequester(String requestedBy) {
        return approvalRepository.findByRequestedBy(requestedBy);
    }

    public Map<String, Object> getApprovalStats() {
        Map<String, Object> stats = new HashMap<>();
        List<ConfigApproval> all = approvalRepository.findAll();

        for (ConfigApproval.ApprovalStatus status : ConfigApproval.ApprovalStatus.values()) {
            long count = all.stream().filter(a -> status == a.getStatus()).count();
            stats.put(status.name().toLowerCase() + "Count", count);
        }

        stats.put("totalRequests", all.size());

        Map<String, Long> pendingByLevel = new HashMap<>();
        for (ConfigApproval.ApprovalLevel level : ConfigApproval.ApprovalLevel.values()) {
            long count = all.stream()
                    .filter(a -> a.getCurrentLevel() == level)
                    .filter(a -> a.getStatus() == ConfigApproval.ApprovalStatus.PENDING ||
                            a.getStatus() == ConfigApproval.ApprovalStatus.IN_PROGRESS)
                    .count();
            pendingByLevel.put(level.name(), count);
        }
        stats.put("pendingByLevel", pendingByLevel);

        return stats;
    }

    public boolean requiresApproval(ConfigDiff diff, String serviceName) {
        if (diffService.isSensitiveChange(diff)) {
            return true;
        }
        if (diff.getTotalChanges() > 10) {
            return true;
        }
        return false;
    }
}
