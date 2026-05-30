package com.sessionguard.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class VerifySessionRequest {

    @NotBlank(message = "sessionId is required")
    private String sessionId;

    private String businessScenario;
}
