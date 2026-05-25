package com.survey.repository;

import com.survey.entity.SmsRecord;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface SmsRecordRepository extends MongoRepository<SmsRecord, String> {

    List<SmsRecord> findByCampaignId(String campaignId);

    List<SmsRecord> findBySurveyId(String surveyId);

    boolean existsBySurveyIdAndPhoneNumber(String surveyId, String phoneNumber);
}
