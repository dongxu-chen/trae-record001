package com.emailmarketing.service;

import com.emailmarketing.dto.EmailSendMessage;
import com.emailmarketing.entity.EmailSendLog;
import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
public class EmailSendService {

    @Autowired
    private JavaMailSender javaMailSender;

    @Autowired
    private DomainRateLimitService rateLimitService;

    @Autowired
    private EmailSendLogService sendLogService;

    public boolean sendEmail(EmailSendMessage message) {
        if (!rateLimitService.tryAcquire(message.getToEmail())) {
            return false;
        }

        try {
            MimeMessage mimeMessage = javaMailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(mimeMessage, true, "UTF-8");
            helper.setTo(message.getToEmail());
            helper.setSubject(message.getSubject());
            helper.setText(message.getContent(), true);
            javaMailSender.send(mimeMessage);
            
            updateSendLog(message.getSendLogId(), true, null);
            return true;
        } catch (MessagingException e) {
            updateSendLog(message.getSendLogId(), false, e.getMessage());
            return false;
        }
    }

    private void updateSendLog(Long sendLogId, boolean success, String errorMsg) {
        EmailSendLog log = new EmailSendLog();
        log.setId(sendLogId);
        log.setSendStatus(success ? 1 : 2);
        log.setErrorMsg(errorMsg);
        log.setSentAt(LocalDateTime.now());
        sendLogService.updateById(log);
    }
}
