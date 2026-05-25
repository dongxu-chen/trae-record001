package com.survey.service;

import com.survey.dto.SurveyCreateRequest;
import com.survey.entity.Question;
import com.survey.entity.Survey;
import com.survey.enums.SurveyStatus;
import com.survey.exception.BusinessException;
import com.survey.repository.SurveyRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class SurveyService {

    private final SurveyRepository surveyRepository;
    private final LogicJumpService logicJumpService;

    @Transactional
    public Survey createSurvey(SurveyCreateRequest request) {
        Survey survey = new Survey();
        survey.setTitle(request.getTitle());
        survey.setDescription(request.getDescription());
        survey.setCreatorId(request.getCreatorId() != null ? request.getCreatorId() : "anonymous");
        survey.setStatus(SurveyStatus.DRAFT);
        survey.setQuestions(request.getQuestions());
        survey.setLogicJumps(request.getLogicJumps());
        survey.setAnonymous(request.getAnonymous() != null ? request.getAnonymous() : true);
        survey.setAntiDuplicateType(request.getAntiDuplicateType());
        survey.setTimeLimit(request.getTimeLimit());
        survey.setStartTime(request.getStartTime());
        survey.setEndTime(request.getEndTime());
        survey.setTotalResponses(0);

        if (survey.getQuestions() != null) {
            for (Question question : survey.getQuestions()) {
                if (question.getId() == null) {
                    question.setId(UUID.randomUUID().toString());
                }
                if (question.getSurveyId() == null) {
                    question.setSurveyId(survey.getId());
                }
            }
        }

        logicJumpService.validateLogicJumps(survey);

        return surveyRepository.save(survey);
    }

    @Transactional
    public Survey updateSurvey(String id, SurveyCreateRequest request) {
        Survey survey = getSurvey(id);

        if (survey.getStatus() == SurveyStatus.PUBLISHED) {
            throw new BusinessException("已发布的问卷不能修改");
        }

        survey.setTitle(request.getTitle());
        survey.setDescription(request.getDescription());
        survey.setQuestions(request.getQuestions());
        survey.setLogicJumps(request.getLogicJumps());
        survey.setAnonymous(request.getAnonymous() != null ? request.getAnonymous() : true);
        survey.setAntiDuplicateType(request.getAntiDuplicateType());
        survey.setTimeLimit(request.getTimeLimit());
        survey.setStartTime(request.getStartTime());
        survey.setEndTime(request.getEndTime());

        if (survey.getQuestions() != null) {
            for (Question question : survey.getQuestions()) {
                if (question.getId() == null) {
                    question.setId(UUID.randomUUID().toString());
                }
            }
        }

        logicJumpService.validateLogicJumps(survey);

        return surveyRepository.save(survey);
    }

    @Transactional
    public Survey publishSurvey(String id) {
        Survey survey = getSurvey(id);

        if (survey.getQuestions() == null || survey.getQuestions().isEmpty()) {
            throw new BusinessException("问卷至少需要一个问题");
        }

        logicJumpService.validateLogicJumps(survey);

        String shareCode = generateShareCode();
        survey.setShareCode(shareCode);
        survey.setStatus(SurveyStatus.PUBLISHED);

        return surveyRepository.save(survey);
    }

    @Transactional
    public Survey closeSurvey(String id) {
        Survey survey = getSurvey(id);
        survey.setStatus(SurveyStatus.CLOSED);
        return surveyRepository.save(survey);
    }

    public void deleteSurvey(String id) {
        Survey survey = getSurvey(id);
        if (survey.getStatus() == SurveyStatus.PUBLISHED) {
            throw new BusinessException("请先关闭问卷再删除");
        }
        surveyRepository.deleteById(id);
    }

    public Survey getSurvey(String id) {
        return surveyRepository.findById(id)
                .orElseThrow(() -> new BusinessException("问卷不存在"));
    }

    public Survey getSurveyByShareCode(String shareCode) {
        return surveyRepository.findPublishedByShareCode(shareCode)
                .orElseThrow(() -> new BusinessException("问卷不存在或未发布"));
    }

    public List<Survey> getSurveysByCreator(String creatorId) {
        return surveyRepository.findByCreatorId(creatorId);
    }

    private String generateShareCode() {
        String shareCode;
        int attempts = 0;
        do {
            shareCode = UUID.randomUUID().toString().substring(0, 8);
            attempts++;
        } while (surveyRepository.existsByShareCode(shareCode) && attempts < 10);
        return shareCode;
    }
}
