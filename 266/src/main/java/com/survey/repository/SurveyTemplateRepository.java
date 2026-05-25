package com.survey.repository;

import com.survey.entity.SurveyTemplate;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.data.mongodb.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface SurveyTemplateRepository extends MongoRepository<SurveyTemplate, String> {

    List<SurveyTemplate> findByCategory(String category);

    @Query("{'$text': {'$search': ?0}}")
    List<SurveyTemplate> searchByText(String keyword);

    @Query("{'tags': {'$in': ?0}}")
    List<SurveyTemplate> findByTagsContaining(List<String> tags);

    List<SurveyTemplate> findTop10ByOrderByUsageCountDesc();
}
