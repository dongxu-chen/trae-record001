package com.sessionguard.dto;

import com.sessionguard.model.ThreatIntel;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AddThreatRequest {

    @NotBlank(message = "ipAddress is required")
    private String ipAddress;

    @NotNull(message = "threatType is required")
    private ThreatIntel.ThreatType threatType;

    @NotNull(message = "severity is required")
    private ThreatIntel.ThreatSeverity severity;

    private String source;

    private String description;

    private String[] tags;
}
