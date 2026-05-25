package com.survey.model;

import lombok.Data;
import java.util.List;

@Data
public class LogicJump {
    private String id;
    private String fromQuestionId;
    private String conditionType;
    private List<String> conditionValues;
    private String toQuestionId;
}
