package com.mfa.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TotpVerificationResult {

    private boolean valid;
    private int driftOffset;
    private int timeStep;
    private String serverTime;
    private String errorMessage;
}
