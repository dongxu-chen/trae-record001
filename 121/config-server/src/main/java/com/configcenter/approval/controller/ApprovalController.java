package com.configcenter.approval.controller;

import com.configcenter.approval.entity.ConfigApproval;
import com.configcenter.approval.service.ApprovalService;
import com.configcenter.audit.entity.ConfigAuditLog;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/approval")
public class ApprovalController {

    @Autowired
    private ApprovalService approvalService;

    @PostMapping("/requests")
    public ResponseEntity<ConfigApproval> createRequest(@RequestBody ApprovalRequest request) {
        ConfigApproval approval = approvalService.createRequest(
                request.getServiceName(),
                request.getProfile(),
                request.getLabel(),
                request.getTargetConfig(),
                request.getRequestedBy(),
                request.getChangeReason()
        );
        return ResponseEntity.ok(approval);
    }

    @GetMapping("/requests")
    public ResponseEntity<List<ConfigApproval>> getRequests(
            @RequestParam(required = false) String serviceName,
            @RequestParam(required = false) ConfigApproval.ApprovalStatus status,
            @RequestParam(required = false) String requestedBy) {
        List<ConfigApproval> requests;
        if (serviceName != null) {
            requests = approvalService.getApprovalsByService(serviceName);
        } else if (status != null) {
            requests = approvalService.getApprovalsByStatus(status);
        } else if (requestedBy != null) {
            requests = approvalService.getApprovalsByRequester(requestedBy);
        } else {
            requests = approvalService.getAllApprovals();
        }
        return ResponseEntity.ok(requests);
    }

    @GetMapping("/requests/{id}")
    public ResponseEntity<ConfigApproval> getRequest(@PathVariable String id) {
        return approvalService.getApproval(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PutMapping("/requests/{id}/approve")
    public ResponseEntity<ConfigApproval> approve(
            @PathVariable String id,
            @RequestBody ApprovalActionRequest request) {
        ConfigApproval approval = approvalService.approve(
                id, request.getApprover(), request.getComment(), request.getLevel());
        return ResponseEntity.ok(approval);
    }

    @PutMapping("/requests/{id}/reject")
    public ResponseEntity<ConfigApproval> reject(
            @PathVariable String id,
            @RequestBody ApprovalActionRequest request) {
        ConfigApproval approval = approvalService.reject(
                id, request.getApprover(), request.getComment(), request.getLevel());
        return ResponseEntity.ok(approval);
    }

    @PutMapping("/requests/{id}/request-change")
    public ResponseEntity<ConfigApproval> requestChange(
            @PathVariable String id,
            @RequestBody ApprovalActionRequest request) {
        ConfigApproval approval = approvalService.requestChange(
                id, request.getApprover(), request.getComment(), request.getLevel());
        return ResponseEntity.ok(approval);
    }

    @PutMapping("/requests/{id}/cancel")
    public ResponseEntity<ConfigApproval> cancel(
            @PathVariable String id,
            @RequestBody CancelRequest request) {
        ConfigApproval approval = approvalService.cancel(id, request.getCancelledBy());
        return ResponseEntity.ok(approval);
    }

    @PostMapping("/requests/{id}/publish")
    public ResponseEntity<ConfigAuditLog> publish(
            @PathVariable String id,
            @RequestBody PublishRequest request) {
        ConfigAuditLog auditLog = approvalService.publishApprovedConfig(id, request.getPublishedBy());
        return ResponseEntity.ok(auditLog);
    }

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getApprovalStats() {
        return ResponseEntity.ok(approvalService.getApprovalStats());
    }

    public static class ApprovalRequest {
        private String serviceName;
        private String profile;
        private String label;
        private Map<String, Object> targetConfig;
        private String requestedBy;
        private String changeReason;

        public String getServiceName() { return serviceName; }
        public void setServiceName(String serviceName) { this.serviceName = serviceName; }
        public String getProfile() { return profile; }
        public void setProfile(String profile) { this.profile = profile; }
        public String getLabel() { return label; }
        public void setLabel(String label) { this.label = label; }
        public Map<String, Object> getTargetConfig() { return targetConfig; }
        public void setTargetConfig(Map<String, Object> targetConfig) { this.targetConfig = targetConfig; }
        public String getRequestedBy() { return requestedBy; }
        public void setRequestedBy(String requestedBy) { this.requestedBy = requestedBy; }
        public String getChangeReason() { return changeReason; }
        public void setChangeReason(String changeReason) { this.changeReason = changeReason; }
    }

    public static class ApprovalActionRequest {
        private String approver;
        private String comment;
        private ConfigApproval.ApprovalLevel level;

        public String getApprover() { return approver; }
        public void setApprover(String approver) { this.approver = approver; }
        public String getComment() { return comment; }
        public void setComment(String comment) { this.comment = comment; }
        public ConfigApproval.ApprovalLevel getLevel() { return level; }
        public void setLevel(ConfigApproval.ApprovalLevel level) { this.level = level; }
    }

    public static class CancelRequest {
        private String cancelledBy;

        public String getCancelledBy() { return cancelledBy; }
        public void setCancelledBy(String cancelledBy) { this.cancelledBy = cancelledBy; }
    }

    public static class PublishRequest {
        private String publishedBy;

        public String getPublishedBy() { return publishedBy; }
        public void setPublishedBy(String publishedBy) { this.publishedBy = publishedBy; }
    }
}
