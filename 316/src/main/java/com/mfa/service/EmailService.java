package com.mfa.service;

public interface EmailService {

    void sendVerificationCode(String email, String code);
}
