package com.survey.repository;

import com.survey.entity.VoteRecord;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface VoteRecordRepository extends MongoRepository<VoteRecord, String> {

    List<VoteRecord> findBySurveyId(String surveyId);

    Optional<VoteRecord> findBySurveyIdAndRespondentIdentifier(String surveyId, String respondentIdentifier);

    long countBySurveyId(String surveyId);

    boolean existsBySurveyIdAndRespondentIdentifier(String surveyId, String respondentIdentifier);

    boolean existsBySurveyIdAndRespondentIp(String surveyId, String respondentIp);
}
