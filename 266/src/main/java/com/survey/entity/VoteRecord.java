package com.survey.entity;

import com.survey.model.DeviceInfo;
import lombok.Data;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Document(collection = "vote_records")
@CompoundIndex(name = "survey_respondent_idx", def = "{'surveyId': 1, 'respondentIdentifier': 1}", unique = true)
public class VoteRecord {
    @Id
    private String id;
    private String surveyId;
    private String respondentIdentifier;
    private String respondentIp;
    private List<Answer> answers;
    private Integer timeTaken;
    private LocalDateTime startTime;
    private DeviceInfo deviceInfo;
    private Boolean completed;
    @CreatedDate
    private LocalDateTime submittedAt;
}

