package com.survey.entity;

import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class Answer {
    private String questionId;
    private String questionType;
    private List<String> selectedOptions;
    private String textValue;
    private Map<String, String> matrixValues;
}
