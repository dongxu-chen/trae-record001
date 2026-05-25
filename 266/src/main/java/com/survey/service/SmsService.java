package com.survey.service;

import com.survey.entity.SmsRecord;
import com.survey.repository.SmsRecordRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class SmsService {

    private final SmsRecordRepository smsRecordRepository;

    public boolean sendSms(String phoneNumber, String content, String surveyId, String campaignId) {
        SmsRecord record = new SmsRecord();
        record.setId(UUID.randomUUID().toString());
        record.setCampaignId(campaignId);
        record.setSurveyId(surveyId);
        record.setPhoneNumber(phoneNumber);
        record.setContent(content);
        record.setSmsProvider("MOCK");
        record.setCreatedAt(LocalDateTime.now());

        try {
            boolean success = mockSendSms(phoneNumber, content);
            if (success) {
                record.setStatus("SUCCESS");
                record.setMessageId(UUID.randomUUID().toString());
                record.setSentAt(LocalDateTime.now());
                smsRecordRepository.save(record);
                log.info("短信发送成功: {}", phoneNumber);
                return true;
            } else {
                record.setStatus("FAILED");
                record.setErrorMessage("模拟发送失败");
                smsRecordRepository.save(record);
                log.warn("短信发送失败: {}", phoneNumber);
                return false;
            }
        } catch (Exception e) {
            record.setStatus("FAILED");
            record.setErrorMessage(e.getMessage());
            smsRecordRepository.save(record);
            log.error("短信发送异常: {}", phoneNumber, e);
            return false;
        }
    }

    private boolean mockSendSms(String phoneNumber, String content) {
        log.info("MOCK发送短信到: {}, 内容: {}", phoneNumber, content);
        return phoneNumber != null && phoneNumber.length() >= 11;
    }

    public boolean validatePhoneNumber(String phoneNumber) {
        if (phoneNumber == null) {
            return false;
        }
        String cleanNumber = phoneNumber.replaceAll("[^0-9]", "");
        return cleanNumber.length() == 11 && cleanNumber.startsWith("1");
    }

    public String formatPhoneNumber(String phoneNumber) {
        if (phoneNumber == null) {
            return null;
        }
        return phoneNumber.replaceAll("[^0-9]", "");
    }
}
