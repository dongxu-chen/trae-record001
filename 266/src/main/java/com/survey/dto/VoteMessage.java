package com.survey.dto;

import com.survey.entity.Answer;
import lombok.Data;

import java.util.List;

@Data
public class VoteMessage {
    private String surveyId;
    private List<Answer> answers;
    private String voteRecordId;
}
