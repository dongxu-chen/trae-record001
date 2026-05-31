package com.depguard.entity;

import com.depguard.enums.BuildTool;
import com.depguard.enums.ScanStatus;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "repositories")
public class Repository {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;

    @Column(nullable = false, unique = true)
    private String fullName;

    @Column(name = "html_url")
    private String htmlUrl;

    @Column(name = "default_branch")
    private String defaultBranch;

    @Enumerated(EnumType.STRING)
    @Column(name = "build_tool")
    private BuildTool buildTool;

    @Column(name = "last_scan_time")
    private LocalDateTime lastScanTime;

    @Enumerated(EnumType.STRING)
    @Column(name = "scan_status")
    private ScanStatus scanStatus = ScanStatus.IDLE;

    @Column(name = "health_score")
    private Double healthScore;

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
        if (scanStatus == null) {
            scanStatus = ScanStatus.IDLE;
        }
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
