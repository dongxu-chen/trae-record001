package com.survey.dto;

import com.survey.enums.AntiDuplicateType;
import com.survey.model.LogicJump;
import com.survey.entity.Question;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
public class SurveyCreateRequest {
    @NotBlank(message = "问卷标题不能为空")
    private String title;
    private String description;
    private String creatorId;
    private List<Question> questions;
    private List<LogicJump> logicJumps;
    private Boolean anonymous;
    private AntiDuplicateType antiDuplicateType;
    private Integer timeLimit;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
}
