package com.survey.entity;

import com.survey.enums.QuestionType;
import lombok.Data;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Document(collection = "survey_templates")
public class SurveyTemplate {
    @Id
    private String id;
    private String name;
    private String category;
    private String description;
    private List<String> tags;
    private String title;
    private String surveyDescription;
    private List<TemplateQuestion> questions;
    private Integer usageCount;
    private Double rating;
    @CreatedDate
    private LocalDateTime createdAt;
}

@Data
class TemplateQuestion {
    private String title;
    private String description;
    private QuestionType type;
    private Boolean required;
    private List<String> options;
    private List<String> matrixRows;
    private List<String> matrixColumns;
}
