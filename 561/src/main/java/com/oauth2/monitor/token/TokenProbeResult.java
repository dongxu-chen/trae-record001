package com.oauth2.monitor.token;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TokenProbeResult {

    private String tokenValue;
    private boolean active;
    private boolean validSignature;
    private boolean notExpired;
    private boolean notRevoked;
    private boolean issuerValid;
    private boolean audienceValid;
    private String errorMessage;
    private Instant probedAt;
    private long probeLatencyMs;
    private long timeToExpirySeconds;

    public boolean isCompletelyValid() {
        return active && validSignature && notExpired && notRevoked && issuerValid && audienceValid;
    }

    public String getValidationSummary() {
        if (isCompletelyValid()) {
            return "VALID";
        }
        StringBuilder sb = new StringBuilder("INVALID: ");
        if (!active) sb.append("inactive, ");
        if (!validSignature) sb.append("bad-signature, ");
        if (!notExpired) sb.append("expired, ");
        if (!notRevoked) sb.append("revoked, ");
        if (!issuerValid) sb.append("bad-issuer, ");
        if (!audienceValid) sb.append("bad-audience, ");
        return sb.substring(0, sb.length() - 2);
    }
}
