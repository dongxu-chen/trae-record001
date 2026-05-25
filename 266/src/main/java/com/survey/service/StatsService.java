package com.survey.service;

import com.survey.dto.QuestionStats;
import com.survey.dto.SurveyStats;
import com.survey.entity.Answer;
import com.survey.entity.Survey;
import com.survey.enums.QuestionType;
import com.survey.exception.BusinessException;
import com.survey.repository.SurveyRepository;
import com.survey.repository.VoteRecordRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.TimeUnit;

@Service
@RequiredArgsConstructor
public class StatsService {

    private final RedisTemplate<String, Object> redisTemplate;
    private final SurveyRepository surveyRepository;
    private final VoteRecordRepository voteRecordRepository;

    @Value("${survey.redis.stats-prefix}")
    private String statsPrefix;

    @Value("${survey.redis.expire-hours}")
    private long expireHours;

    public void updateStats(String surveyId, List<Answer> answers) {
        String key = statsPrefix + surveyId;

        redisTemplate.execute((RedisCallback<Void>) connection -> {
            byte[] keyBytes = key.getBytes();

            connection.hIncrBy(keyBytes, "totalResponses".getBytes(), 1);

            for (Answer answer : answers) {
                String questionId = answer.getQuestionId();
                String questionType = answer.getQuestionType();

                if (QuestionType.SINGLE_CHOICE.name().equals(questionType) ||
                        QuestionType.MULTIPLE_CHOICE.name().equals(questionType)) {
                    List<String> options = answer.getSelectedOptions();
                    if (options != null) {
                        for (String optionId : options) {
                            String optionKey = "question:" + questionId + ":option:" + optionId;
                            connection.hIncrBy(keyBytes, optionKey.getBytes(), 1);
                        }
                    }
                    String responseKey = "question:" + questionId + ":responses";
                    connection.hIncrBy(keyBytes, responseKey.getBytes(), 1);
                } else if (QuestionType.MATRIX.name().equals(questionType)) {
                    Map<String, String> matrixValues = answer.getMatrixValues();
                    if (matrixValues != null) {
                        for (Map.Entry<String, String> entry : matrixValues.entrySet()) {
                            String rowId = entry.getKey();
                            String colId = entry.getValue();
                            String matrixKey = "question:" + questionId + ":matrix:" + rowId + ":" + colId;
                            connection.hIncrBy(keyBytes, matrixKey.getBytes(), 1);
                        }
                    }
                    String responseKey = "question:" + questionId + ":responses";
                    connection.hIncrBy(keyBytes, responseKey.getBytes(), 1);
                } else if (QuestionType.TEXT.name().equals(questionType)) {
                    String responseKey = "question:" + questionId + ":responses";
                    connection.hIncrBy(keyBytes, responseKey.getBytes(), 1);
                }
            }

            connection.expire(keyBytes, expireHours * 3600);

            return null;
        });
    }

    public SurveyStats getSurveyStats(String surveyId) {
        Survey survey = surveyRepository.findById(surveyId)
                .orElseThrow(() -> new BusinessException("问卷不存在"));

        String key = statsPrefix + surveyId;
        Map<Object, Object> redisStats = redisTemplate.opsForHash().entries(key);

        SurveyStats stats = new SurveyStats();
        stats.setSurveyId(surveyId);
        stats.setSurveyTitle(survey.getTitle());

        Integer totalResponses = getIntValue(redisStats.get("totalResponses"));
        if (totalResponses == null || totalResponses == 0) {
            totalResponses = (int) voteRecordRepository.countBySurveyId(surveyId);
        }
        stats.setTotalResponses(totalResponses);

        List<QuestionStats> questionStatsList = new ArrayList<>();
        if (survey.getQuestions() != null) {
            for (com.survey.entity.Question question : survey.getQuestions()) {
                QuestionStats qs = new QuestionStats();
                qs.setQuestionId(question.getId());
                qs.setQuestionTitle(question.getTitle());
                qs.setQuestionType(question.getType().name());

                Integer responses = getIntValue(redisStats.get("question:" + question.getId() + ":responses"));
                qs.setTotalResponses(responses != null ? responses : 0);

                if (question.getType() == QuestionType.SINGLE_CHOICE || question.getType() == QuestionType.MULTIPLE_CHOICE) {
                    Map<String, Integer> optionCounts = new HashMap<>();
                    if (question.getOptions() != null) {
                        for (com.survey.model.Option option : question.getOptions()) {
                            String optionKey = "question:" + question.getId() + ":option:" + option.getId();
                            Integer count = getIntValue(redisStats.get(optionKey));
                            optionCounts.put(option.getId(), count != null ? count : 0);
                        }
                    }
                    qs.setOptionCounts(optionCounts);
                } else if (question.getType() == QuestionType.MATRIX) {
                    Map<String, Map<String, Integer>> matrixCounts = new HashMap<>();
                    if (question.getMatrixRows() != null) {
                        for (com.survey.model.MatrixRow row : question.getMatrixRows()) {
                            Map<String, Integer> rowCounts = new HashMap<>();
                            if (question.getMatrixColumns() != null) {
                                for (com.survey.model.MatrixColumn col : question.getMatrixColumns()) {
                                    String matrixKey = "question:" + question.getId() + ":matrix:" + row.getId() + ":" + col.getId();
                                    Integer count = getIntValue(redisStats.get(matrixKey));
                                    rowCounts.put(col.getId(), count != null ? count : 0);
                                }
                            }
                            matrixCounts.put(row.getId(), rowCounts);
                        }
                    }
                    qs.setMatrixCounts(matrixCounts);
                } else if (question.getType() == QuestionType.TEXT) {
                    qs.setTextResponseCount(qs.getTotalResponses());
                }

                questionStatsList.add(qs);
            }
        }
        stats.setQuestionStats(questionStatsList);

        return stats;
    }

    private Integer getIntValue(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Integer) {
            return (Integer) value;
        }
        if (value instanceof Long) {
            return ((Long) value).intValue();
        }
        return Integer.parseInt(value.toString());
    }
}
