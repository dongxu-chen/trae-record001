package com.survey.service;

import com.survey.config.RabbitMQConfig;
import com.survey.dto.SmsCampaignRequest;
import com.survey.entity.SmsCampaign;
import com.survey.entity.Survey;
import com.survey.exception.BusinessException;
import com.survey.repository.SmsCampaignRepository;
import com.survey.repository.SmsRecordRepository;
import com.survey.repository.SurveyRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class SmsCampaignService {

    private final SmsCampaignRepository campaignRepository;
    private final SmsRecordRepository smsRecordRepository;
    private final SurveyRepository surveyRepository;
    private final SmsService smsService;
    private final DistributionService distributionService;
    private final RabbitTemplate rabbitTemplate;

    @Value("${survey.base-url}")
    private String baseUrl;

    public SmsCampaign createCampaign(SmsCampaignRequest request) {
        Survey survey = surveyRepository.findById(request.getSurveyId())
                .orElseThrow(() -> new BusinessException("问卷不存在"));

        if (survey.getShareCode() == null) {
            throw new BusinessException("问卷未发布，请先发布问卷");
        }

        List<String> validatedPhones = validateAndDeduplicatePhones(request.getPhoneNumbers());
        if (validatedPhones.isEmpty()) {
            throw new BusinessException("没有有效的手机号");
        }

        SmsCampaign campaign = new SmsCampaign();
        campaign.setSurveyId(request.getSurveyId());
        campaign.setName(request.getName() != null ? request.getName() : "短信投放 - " + survey.getTitle());
        campaign.setDescription(request.getDescription());
        campaign.setSmsTemplate(request.getSmsTemplate() != null ? request.getSmsTemplate() :
                "您好！诚邀您参与【" + survey.getTitle() + "】调查，点击链接参与：{link}");
        campaign.setPhoneNumbers(validatedPhones);
        campaign.setTotalCount(validatedPhones.size());
        campaign.setSentCount(0);
        campaign.setSuccessCount(0);
        campaign.setFailCount(0);
        campaign.setStatus(request.getScheduledTime() != null ? "SCHEDULED" : "PENDING");
        campaign.setScheduledTime(request.getScheduledTime());
        campaign.setCreatedAt(LocalDateTime.now());

        return campaignRepository.save(campaign);
    }

    public SmsCampaign startCampaign(String campaignId) {
        SmsCampaign campaign = campaignRepository.findById(campaignId)
                .orElseThrow(() -> new BusinessException("投放任务不存在"));

        if ("RUNNING".equals(campaign.getStatus())) {
            throw new BusinessException("投放任务正在进行中");
        }
        if ("COMPLETED".equals(campaign.getStatus())) {
            throw new BusinessException("投放任务已完成");
        }

        campaign.setStatus("RUNNING");
        campaignRepository.save(campaign);

        sendCampaignMessages(campaign);

        return campaign;
    }

    private void sendCampaignMessages(SmsCampaign campaign) {
        Survey survey = surveyRepository.findById(campaign.getSurveyId()).orElse(null);
        if (survey == null) {
            log.error("问卷不存在: {}", campaign.getSurveyId());
            return;
        }

        String surveyLink = distributionService.getSurveyLink(survey.getShareCode());

        int successCount = 0;
        int failCount = 0;

        for (int i = 0; i < campaign.getPhoneNumbers().size(); i++) {
            String phone = campaign.getPhoneNumbers().get(i);

            if (smsRecordRepository.existsBySurveyIdAndPhoneNumber(campaign.getSurveyId(), phone)) {
                failCount++;
                continue;
            }

            String content = campaign.getSmsTemplate().replace("{link}", surveyLink);

            boolean success = smsService.sendSms(phone, content, campaign.getSurveyId(), campaign.getId());
            if (success) {
                successCount++;
            } else {
                failCount++;
            }

            campaign.setSentCount(i + 1);
            campaign.setSuccessCount(successCount);
            campaign.setFailCount(failCount);

            if (i % 10 == 0) {
                campaignRepository.save(campaign);
            }

            try {
                Thread.sleep(100);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }

        campaign.setStatus("COMPLETED");
        campaignRepository.save(campaign);

        log.info("短信投放完成: 总数={}, 成功={}, 失败={}",
                campaign.getTotalCount(), successCount, failCount);
    }

    private List<String> validateAndDeduplicatePhones(List<String> phoneNumbers) {
        Set<String> uniquePhones = new HashSet<>();
        for (String phone : phoneNumbers) {
            String formatted = smsService.formatPhoneNumber(phone);
            if (smsService.validatePhoneNumber(formatted)) {
                uniquePhones.add(formatted);
            }
        }
        return new ArrayList<>(uniquePhones);
    }

    public List<String> importPhoneNumbers(List<String> phoneNumbers) {
        return phoneNumbers.stream()
                .map(smsService::formatPhoneNumber)
                .filter(smsService::validatePhoneNumber)
                .distinct()
                .collect(Collectors.toList());
    }

    public List<SmsCampaign> getCampaignsBySurvey(String surveyId) {
        return campaignRepository.findBySurveyId(surveyId);
    }

    public SmsCampaign getCampaign(String campaignId) {
        return campaignRepository.findById(campaignId)
                .orElseThrow(() -> new BusinessException("投放任务不存在"));
    }

    public void cancelCampaign(String campaignId) {
        SmsCampaign campaign = campaignRepository.findById(campaignId)
                .orElseThrow(() -> new BusinessException("投放任务不存在"));

        if ("RUNNING".equals(campaign.getStatus())) {
            campaign.setStatus("CANCELLED");
            campaignRepository.save(campaign);
        }
    }
}
