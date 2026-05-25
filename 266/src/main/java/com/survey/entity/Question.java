package com.survey.entity;

import com.survey.enums.QuestionType;
import com.survey.model.MatrixColumn;
import com.survey.model.MatrixRow;
import com.survey.model.Option;
import lombok.Data;
import org.springframework.data.annotation.Id;

import java.util.List;

@Data
public class Question {
    @Id
    private String id;
    private String surveyId;
    private String title;
    private String description;
    private QuestionType type;
    private Boolean required;
    private Integer sortOrder;
    private List<Option> options;
    private List<MatrixRow> matrixRows;
    private List<MatrixColumn> matrixColumns;
    private Integer maxSelect;
}
