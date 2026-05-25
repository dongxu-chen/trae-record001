package com.survey.repository;

import com.survey.entity.SmsCampaign;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface SmsCampaignRepository extends MongoRepository<SmsCampaign, String> {

    List<SmsCampaign> findBySurveyId(String surveyId);

    List<SmsCampaign> findByStatus(String status);
}
