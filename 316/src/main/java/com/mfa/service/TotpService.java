package com.mfa.service;

import com.mfa.dto.TotpSetupResponse;
import com.mfa.dto.TotpVerificationResult;

public interface TotpService {

    TotpSetupResponse generateSecret(String username, String issuer);

    boolean verifyCode(String secret, String code);

    TotpVerificationResult verifyCodeWithDrift(String secret, String code, String userId);

    int getCurrentDriftOffset(String userId);

    void resetDriftOffset(String userId);

    String getQrCodeUri(String secret, String username, String issuer);
}
