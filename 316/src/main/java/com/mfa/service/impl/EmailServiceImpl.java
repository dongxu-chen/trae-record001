package com.mfa.service.impl;

import com.mfa.service.EmailService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class EmailServiceImpl implements EmailService {

    private final JavaMailSender mailSender;

    @Override
    @Async
    public void sendVerificationCode(String email, String code) {
        try {
            SimpleMailMessage message = new SimpleMailMessage();
            message.setTo(email);
            message.setSubject("您的邮箱验证码");
            message.setText("您的验证码是: " + code + "\n\n" +
                    "该验证码10分钟内有效，如非本人操作请忽略此邮件。\n\n" +
                    "此致\nMFA 认证服务团队");

            mailSender.send(message);
            log.info("Email verification code sent to: {}", maskEmail(email));
        } catch (Exception e) {
            log.error("Failed to send email to: {}, error: {}", maskEmail(email), e.getMessage());
            log.info("=== 模拟发送邮件验证码 ===");
            log.info("邮箱: {}", maskEmail(email));
            log.info("验证码: {}", code);
            log.info("邮件内容: 您的验证码是 {}, 10分钟内有效。如非本人操作请忽略。", code);
            log.info("======================");
        }
    }

    private String maskEmail(String email) {
        if (email == null) {
            return null;
        }
        int atIndex = email.indexOf("@");
        if (atIndex <= 0) {
            return email;
        }
        String username = email.substring(0, atIndex);
        String domain = email.substring(atIndex);
        if (username.length() <= 2) {
            return "*" + domain;
        }
        return username.charAt(0) + "***" + username.charAt(username.length() - 1) + domain;
    }
}
