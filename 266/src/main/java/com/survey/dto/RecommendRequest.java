package com.survey.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class RecommendRequest {
    @NotBlank(message = "调查主题不能为空")
    private String topic;
    private String industry;
    private Integer questionCount;
}
