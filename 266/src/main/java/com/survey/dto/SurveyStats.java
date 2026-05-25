package com.survey.dto;

import lombok.Data;
import java.util.List;

@Data
public class SurveyStats {
    private String surveyId;
    private String surveyTitle;
    private Integer totalResponses;
    private List<QuestionStats> questionStats;
}
