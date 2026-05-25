package com.mfa.service;

public interface VerificationCodeService {

    String generateCode(String sessionId, String target, int length, int expireMinutes);

    boolean verifyCode(String sessionId, String target, String code);

    void invalidateCode(String sessionId, String target);

    String getStoredCode(String sessionId, String target);
}
