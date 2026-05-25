package com.survey.dto;

import lombok.Data;
import java.util.Map;

@Data
public class QuestionStats {
    private String questionId;
    private String questionTitle;
    private String questionType;
    private Integer totalResponses;
    private Map<String, Integer> optionCounts;
    private Map<String, Map<String, Integer>> matrixCounts;
    private Integer textResponseCount;
}
