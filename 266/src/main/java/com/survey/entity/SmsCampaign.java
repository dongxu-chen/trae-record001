package com.survey.entity;

import lombok.Data;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Document(collection = "sms_campaigns")
public class SmsCampaign {
    @Id
    private String id;
    private String surveyId;
    private String name;
    private String description;
    private String smsTemplate;
    private List<String> phoneNumbers;
    private Integer totalCount;
    private Integer sentCount;
    private Integer successCount;
    private Integer failCount;
    private String status;
    private LocalDateTime scheduledTime;
    @CreatedDate
    private LocalDateTime createdAt;
}
