package com.depguard.dto;

import com.depguard.enums.BuildTool;
import com.depguard.enums.ScanStatus;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class RepositoryResponse {
    private Long id;
    private String name;
    private String fullName;
    private String htmlUrl;
    private String defaultBranch;
    private BuildTool buildTool;
    private LocalDateTime lastScanTime;
    private ScanStatus scanStatus;
    private Double healthScore;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
