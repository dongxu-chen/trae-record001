package com.depguard.dto;

import com.depguard.enums.ScanStatus;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ScanResponse {
    private Long id;
    private Long repoId;
    private LocalDateTime scanTime;
    private ScanStatus status;
    private Integer totalDeps;
    private Integer conflictCount;
    private Integer vulnerabilityCount;
    private Integer outdatedCount;
}
