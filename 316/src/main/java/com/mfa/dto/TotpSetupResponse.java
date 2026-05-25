package com.mfa.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TotpSetupResponse {

    private String secret;
    private String qrCodeUri;
    private String qrCodeBase64;
    private int digits;
    private int timeStep;
}
