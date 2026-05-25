package com.mfa.service.impl;

import com.mfa.service.SmsService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class SmsServiceImpl implements SmsService {

    @Override
    @Async
    public void sendVerificationCode(String phoneNumber, String code) {
        log.info("=== 发送短信验证码 ===");
        log.info("手机号: {}", maskPhoneNumber(phoneNumber));
        log.info("验证码: {}", code);
        log.info("短信内容: 您的验证码是 {}, 5分钟内有效。如非本人操作请忽略。", code);
        log.info("==================");
    }

    private String maskPhoneNumber(String phoneNumber) {
        if (phoneNumber == null || phoneNumber.length() < 7) {
            return "****";
        }
        return phoneNumber.substring(0, 3) + "****" + phoneNumber.substring(phoneNumber.length() - 4);
    }
}
