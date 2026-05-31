package com.depguard.entity;

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
@Table(name = "scan_results")
public class ScanResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "repo_id", nullable = false)
    private Long repoId;

    @Column(name = "scan_time", nullable = false)
    private LocalDateTime scanTime;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private ScanStatus status;

    @Column(name = "total_deps")
    private Integer totalDeps;

    @Column(name = "conflict_count")
    private Integer conflictCount;

    @Column(name = "vulnerability_count")
    private Integer vulnerabilityCount;

    @Column(name = "outdated_count")
    private Integer outdatedCount;
}
