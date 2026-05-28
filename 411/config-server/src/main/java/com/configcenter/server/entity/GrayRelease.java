package com.configcenter.server.entity;

import lombok.Data;

import javax.persistence.*;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Data
@Entity
@Table(name = "gray_release")
public class GrayRelease {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "application", nullable = false)
    private String application;

    @Column(name = "profile", nullable = false)
    private String profile;

    @Column(name = "label", nullable = false)
    private String label;

    @Column(name = "version", nullable = false)
    private String version;

    @Column(name = "config_content", columnDefinition = "TEXT")
    private String configContent;

    @Column(name = "status", nullable = false)
    @Enumerated(EnumType.STRING)
    private GrayStatus status;

    @Column(name = "strategy", nullable = false)
    @Enumerated(EnumType.STRING)
    private GrayStrategy strategy;

    @Column(name = "gray_ips", columnDefinition = "TEXT")
    private String grayIps;

    @Column(name = "gray_percentage")
    private Integer grayPercentage;

    @Column(name = "pod_label_selector", columnDefinition = "TEXT")
    private String podLabelSelector;

    @Column(name = "created_by", nullable = false)
    private String createdBy;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "approved_by")
    private String approvedBy;

    @Column(name = "approved_at")
    private LocalDateTime approvedAt;

    @Column(name = "full_release_at")
    private LocalDateTime fullReleaseAt;

    public enum GrayStatus {
        PENDING_APPROVAL, IN_GRAY, FULL_RELEASED, ROLLED_BACK, REJECTED
    }

    public enum GrayStrategy {
        IP_LIST, PERCENTAGE, HEADER, POD_LABEL
    }

    @Transient
    public java.util.Map<String, String> getPodLabelMap() {
        if (podLabelSelector == null || podLabelSelector.isEmpty()) {
            return new java.util.HashMap<>();
        }
        java.util.Map<String, String> labels = new java.util.HashMap<>();
        for (String pair : podLabelSelector.split(",")) {
            String[] kv = pair.split("=");
            if (kv.length == 2) {
                labels.put(kv[0].trim(), kv[1].trim());
            }
        }
        return labels;
    }

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        if (status == null) {
            status = GrayStatus.PENDING_APPROVAL;
        }
    }

    @Transient
    public List<String> getGrayIpList() {
        if (grayIps == null || grayIps.isEmpty()) {
            return new ArrayList<>();
        }
        List<String> ips = new ArrayList<>();
        for (String ip : grayIps.split(",")) {
            String trimmed = ip.trim();
            if (!trimmed.isEmpty()) {
                ips.add(trimmed);
            }
        }
        return ips;
    }
}
