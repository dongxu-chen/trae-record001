package com.survey.entity;

import lombok.Data;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;

@Data
@Document(collection = "sms_records")
@CompoundIndex(name = "survey_phone_idx", def = "{'surveyId': 1, 'phoneNumber': 1}", unique = true)
public class SmsRecord {
    @Id
    private String id;
    private String campaignId;
    private String surveyId;
    private String phoneNumber;
    private String content;
    private String status;
    private String errorMessage;
    private String smsProvider;
    private String messageId;
    @CreatedDate
    private LocalDateTime createdAt;
    private LocalDateTime sentAt;
}
