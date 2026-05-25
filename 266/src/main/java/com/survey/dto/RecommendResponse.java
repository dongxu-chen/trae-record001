package com.survey.dto;

import com.survey.entity.Question;
import lombok.Data;

import java.util.List;

@Data
public class RecommendResponse {
    private String title;
    private String description;
    private List<Question> questions;
    private List<String> suggestions;
    private Double matchScore;
}
