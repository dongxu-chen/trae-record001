package com.mfa.service;

public interface SmsService {

    void sendVerificationCode(String phoneNumber, String code);
}
