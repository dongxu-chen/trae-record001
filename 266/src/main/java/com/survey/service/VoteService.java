package com.survey.service;

import com.survey.config.RabbitMQConfig;
import com.survey.dto.VoteMessage;
import com.survey.dto.VoteSubmitRequest;
import com.survey.entity.Answer;
import com.survey.entity.Survey;
import com.survey.entity.VoteRecord;
import com.survey.enums.AntiDuplicateType;
import com.survey.enums.QuestionType;
import com.survey.enums.SurveyStatus;
import com.survey.exception.BusinessException;
import com.survey.repository.SurveyRepository;
import com.survey.repository.VoteRecordRepository;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.TimeUnit;

@Service
@RequiredArgsConstructor
public class VoteService {

    private final VoteRecordRepository voteRecordRepository;
    private final SurveyRepository surveyRepository;
    private final RedisTemplate<String, Object> redisTemplate;
    private final RabbitTemplate rabbitTemplate;
    private final ProfileAnalysisService profileAnalysisService;

    @Value("${survey.redis.vote-lock-prefix}")
    private String voteLockPrefix;

    @Value("${survey.redis.expire-hours}")
    private long expireHours;

    @Transactional
    public VoteRecord submitVote(VoteSubmitRequest request, HttpServletRequest httpRequest) {
        Survey survey = surveyRepository.findById(request.getSurveyId())
                .orElseThrow(() -> new BusinessException("问卷不存在"));

        validateSurvey(survey);
        String respondentIdentifier = getRespondentIdentifier(request, survey, httpRequest);
        checkDuplicateVote(survey, respondentIdentifier, httpRequest);
        validateAnswers(survey, request.getAnswers());

        VoteRecord record = new VoteRecord();
        record.setSurveyId(request.getSurveyId());
        record.setRespondentIdentifier(respondentIdentifier);
        record.setRespondentIp(getClientIp(httpRequest));
        record.setAnswers(request.getAnswers());
        record.setTimeTaken(request.getTimeTaken());
        record.setStartTime(request.getStartTime());
        record.setSubmittedAt(LocalDateTime.now());
        record.setDeviceInfo(profileAnalysisService.parseDeviceInfo(httpRequest));
        record.setCompleted(true);

        record = voteRecordRepository.save(record);

        survey.setTotalResponses(survey.getTotalResponses() + 1);
        surveyRepository.save(survey);

        cacheVoteLock(survey.getId(), respondentIdentifier, httpRequest, survey.getAntiDuplicateType());

        sendVoteMessage(survey.getId(), request.getAnswers(), record.getId());

        return record;
    }

    private void validateSurvey(Survey survey) {
        if (survey.getStatus() != SurveyStatus.PUBLISHED) {
            throw new BusinessException("问卷未发布或已关闭");
        }

        LocalDateTime now = LocalDateTime.now();
        if (survey.getStartTime() != null && now.isBefore(survey.getStartTime())) {
            throw new BusinessException("问卷尚未开始");
        }
        if (survey.getEndTime() != null && now.isAfter(survey.getEndTime())) {
            throw new BusinessException("问卷已结束");
        }
    }

    private String getRespondentIdentifier(VoteSubmitRequest request, Survey survey, HttpServletRequest httpRequest) {
        if (survey.getAnonymous()) {
            if (request.getRespondentIdentifier() != null) {
                return request.getRespondentIdentifier();
            }
            return UUID.randomUUID().toString();
        }
        return request.getRespondentIdentifier() != null ? request.getRespondentIdentifier() : getClientIp(httpRequest);
    }

    private void checkDuplicateVote(Survey survey, String respondentIdentifier, HttpServletRequest httpRequest) {
        AntiDuplicateType antiDuplicateType = survey.getAntiDuplicateType();
        if (antiDuplicateType == null || antiDuplicateType == AntiDuplicateType.NONE) {
            return;
        }

        String lockKey = voteLockPrefix + survey.getId() + ":";
        String ip = getClientIp(httpRequest);

        switch (antiDuplicateType) {
            case IP -> checkIpDuplicate(survey.getId(), lockKey, ip);
            case COOKIE, LOGIN -> checkIdentifierDuplicate(survey.getId(), lockKey, respondentIdentifier);
            case COOKIE_IP -> checkCookieIpDuplicate(survey.getId(), lockKey, respondentIdentifier, ip);
        }
    }

    private void checkIpDuplicate(String surveyId, String lockKey, String ip) {
        if (Boolean.TRUE.equals(redisTemplate.hasKey(lockKey + "ip:" + ip))) {
            throw new BusinessException("您已经提交过了");
        }
        if (voteRecordRepository.existsBySurveyIdAndRespondentIp(surveyId, ip)) {
            throw new BusinessException("您已经提交过了");
        }
    }

    private void checkIdentifierDuplicate(String surveyId, String lockKey, String respondentIdentifier) {
        if (respondentIdentifier != null) {
            if (Boolean.TRUE.equals(redisTemplate.hasKey(lockKey + "id:" + respondentIdentifier))) {
                throw new BusinessException("您已经提交过了");
            }
            if (voteRecordRepository.existsBySurveyIdAndRespondentIdentifier(surveyId, respondentIdentifier)) {
                throw new BusinessException("您已经提交过了");
            }
        }
    }

    private void checkCookieIpDuplicate(String surveyId, String lockKey, String respondentIdentifier, String ip) {
        String combinedKey = "cookie_ip:" + (respondentIdentifier != null ? respondentIdentifier : "unknown") + "_" + ip;
        if (Boolean.TRUE.equals(redisTemplate.hasKey(lockKey + combinedKey))) {
            throw new BusinessException("您已经提交过了");
        }

        boolean existsByIdentifier = respondentIdentifier != null &&
                voteRecordRepository.existsBySurveyIdAndRespondentIdentifier(surveyId, respondentIdentifier);
        boolean existsByIp = voteRecordRepository.existsBySurveyIdAndRespondentIp(surveyId, ip);

        if (existsByIdentifier && existsByIp) {
            throw new BusinessException("您已经提交过了");
        }
    }

    private void cacheVoteLock(String surveyId, String respondentIdentifier, HttpServletRequest httpRequest,
                               AntiDuplicateType antiDuplicateType) {
        String lockKey = voteLockPrefix + surveyId + ":";
        String ip = getClientIp(httpRequest);

        if (antiDuplicateType == null) {
            return;
        }

        switch (antiDuplicateType) {
            case IP -> redisTemplate.opsForValue()
                    .set(lockKey + "ip:" + ip, true, expireHours, TimeUnit.HOURS);
            case COOKIE, LOGIN -> {
                if (respondentIdentifier != null) {
                    redisTemplate.opsForValue()
                            .set(lockKey + "id:" + respondentIdentifier, true, expireHours, TimeUnit.HOURS);
                }
            }
            case COOKIE_IP -> {
                String combinedKey = "cookie_ip:" + (respondentIdentifier != null ? respondentIdentifier : "unknown") + "_" + ip;
                redisTemplate.opsForValue()
                        .set(lockKey + combinedKey, true, expireHours, TimeUnit.HOURS);
            }
        }
    }

    private void validateAnswers(Survey survey, List<Answer> answers) {
        if (survey.getQuestions() == null) {
            return;
        }

        Map<String, com.survey.entity.Question> questionMap = new HashMap<>();
        for (com.survey.entity.Question q : survey.getQuestions()) {
            questionMap.put(q.getId(), q);
        }

        for (Answer answer : answers) {
            com.survey.entity.Question question = questionMap.get(answer.getQuestionId());
            if (question == null) {
                continue;
            }

            if (question.getRequired()) {
                boolean isEmpty = switch (QuestionType.valueOf(answer.getQuestionType())) {
                    case SINGLE_CHOICE, MULTIPLE_CHOICE ->
                            answer.getSelectedOptions() == null || answer.getSelectedOptions().isEmpty();
                    case TEXT -> answer.getTextValue() == null || answer.getTextValue().trim().isEmpty();
                    case MATRIX -> answer.getMatrixValues() == null || answer.getMatrixValues().isEmpty();
                };
                if (isEmpty) {
                    throw new BusinessException("问题 '" + question.getTitle() + "' 是必填项");
                }
            }
        }
    }

    private void sendVoteMessage(String surveyId, List<Answer> answers, String voteRecordId) {
        VoteMessage message = new VoteMessage();
        message.setSurveyId(surveyId);
        message.setAnswers(answers);
        message.setVoteRecordId(voteRecordId);

        rabbitTemplate.convertAndSend(RabbitMQConfig.SURVEY_EXCHANGE, RabbitMQConfig.STATS_ROUTING_KEY, message);
    }

    private String getClientIp(HttpServletRequest request) {
        String xForwardedFor = request.getHeader("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }

    public List<VoteRecord> getVoteRecords(String surveyId) {
        return voteRecordRepository.findBySurveyId(surveyId);
    }
}
