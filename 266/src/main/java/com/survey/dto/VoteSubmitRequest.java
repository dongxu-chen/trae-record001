package com.survey.dto;

import com.survey.entity.Answer;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
public class VoteSubmitRequest {
    @NotBlank(message = "问卷ID不能为空")
    private String surveyId;
    private String respondentIdentifier;
    @NotEmpty(message = "答案不能为空")
    private List<Answer> answers;
    private Integer timeTaken;
    private LocalDateTime startTime;
}
