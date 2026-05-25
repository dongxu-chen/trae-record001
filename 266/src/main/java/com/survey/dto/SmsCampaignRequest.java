package com.survey.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
public class SmsCampaignRequest {
    @NotBlank(message = "问卷ID不能为空")
    private String surveyId;
    private String name;
    private String description;
    private String smsTemplate;
    @NotEmpty(message = "手机号列表不能为空")
    private List<String> phoneNumbers;
    private LocalDateTime scheduledTime;
}
