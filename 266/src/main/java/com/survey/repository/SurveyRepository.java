package com.survey.repository;

import com.survey.entity.Survey;
import com.survey.enums.SurveyStatus;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.data.mongodb.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface SurveyRepository extends MongoRepository<Survey, String> {

    Optional<Survey> findByShareCode(String shareCode);

    List<Survey> findByCreatorId(String creatorId);

    List<Survey> findByStatus(SurveyStatus status);

    @Query("{'status': 'PUBLISHED', 'shareCode': ?0}")
    Optional<Survey> findPublishedByShareCode(String shareCode);

    boolean existsByShareCode(String shareCode);
}
