package com.survey.entity;

import com.survey.enums.AntiDuplicateType;
import com.survey.enums.SurveyStatus;
import com.survey.model.LogicJump;
import lombok.Data;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Document(collection = "surveys")
public class Survey {
    @Id
    private String id;
    private String title;
    private String description;
    private String creatorId;
    private SurveyStatus status;
    private List<Question> questions;
    private List<LogicJump> logicJumps;
    private Boolean anonymous;
    private AntiDuplicateType antiDuplicateType;
    private Integer timeLimit;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private String shareCode;
    private String qrCodePath;
    private Integer totalResponses;
    @CreatedDate
    private LocalDateTime createdAt;
    @LastModifiedDate
    private LocalDateTime updatedAt;
}
