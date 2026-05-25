package com.sms.platform.service;

import cn.hutool.core.util.IdUtil;
import cn.hutool.core.util.RandomUtil;
import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sms.platform.common.enums.SendStatusEnum;
import com.sms.platform.common.enums.SmsTypeEnum;
import com.sms.platform.common.exception.BusinessException;
import com.sms.platform.dto.SendSmsDTO;
import com.sms.platform.dto.SmsSendResult;
import com.sms.platform.entity.SmsSendRecord;
import com.sms.platform.entity.SmsSignature;
import com.sms.platform.entity.SmsTemplate;
import com.sms.platform.entity.SmsChannelConfig;
import com.sms.platform.mapper.SmsSendRecordMapper;
import com.sms.platform.mapper.SmsSignatureMapper;
import com.sms.platform.mapper.SmsTemplateMapper;
import com.sms.platform.sdk.SmsProvider;
import com.sms.platform.sdk.SmsProviderFactory;
import com.sms.platform.util.RedisUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import javax.annotation.Resource;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;

@Slf4j
@Service
public class SmsSendService {

    @Resource
    private BlacklistService blacklistService;

    @Resource
    private RateLimiterService rateLimiterService;

    @Resource
    private ChannelManagerService channelManagerService;

    @Resource
    private SmsSignatureMapper signatureMapper;

    @Resource
    private SmsTemplateMapper templateMapper;

    @Resource
    private SmsSendRecordMapper sendRecordMapper;

    @Resource
    private RedisUtil redisUtil;

    @Resource
    private ObjectMapper objectMapper;

    @Resource
    private ReceiptService receiptService;

    @Resource
    private ContentSecurityService contentSecurityService;

    @Resource
    private SendTimePolicyService sendTimePolicyService;

    @Resource
    private MobileLocationService mobileLocationService;

    @Value("${sms.verification.expire-minutes:5}")
    private int verifyCodeExpireMinutes;

    @Value("${sms.verification.length:6}")
    private int verifyCodeLength;

    private static final String VERIFY_CODE_KEY_PREFIX = "sms:verify:code:";
    private static final Pattern MOBILE_PATTERN = Pattern.compile("^1[3-9]\\d{9}$");

    public SmsSendResult sendSms(SendSmsDTO dto) {
        String serialNo = IdUtil.fastSimpleUUID();

        if (!validateMobile(dto.getMobile())) {
            return buildFailedResult(serialNo, null, "手机号格式不正确");
        }

        SmsTypeEnum smsTypeEnum = SmsTypeEnum.getByCode(dto.getSmsType());
        if (smsTypeEnum == null) {
            return buildFailedResult(serialNo, null, "短信类型不正确");
        }

        SendTimePolicyService.TimeCheckResult timeResult = sendTimePolicyService.checkSendAllowed(dto.getSmsType());
        if (!timeResult.isAllowed()) {
            saveSendRecord(dto, serialNo, null, SendStatusEnum.TIME_POLICY_LIMIT, timeResult.getReason(), null, null,
                    null, null, null, null, null, null, null, null);
            return new SmsSendResult(false, serialNo, null, timeResult.getReason(), null);
        }

        if (blacklistService.isBlacklisted(dto.getMobile(), dto.getSmsType())) {
            saveSendRecord(dto, serialNo, null, SendStatusEnum.BLACKLIST, "手机号在黑名单中", null, null);
            return new SmsSendResult(false, serialNo, null, "手机号在黑名单中", null);
        }

        SmsChannelConfig channelConfig = channelManagerService.selectChannelByType(dto.getSmsType());
        if (channelConfig == null) {
            return buildFailedResult(serialNo, null, "无可用通道");
        }

        if (!rateLimiterService.tryAcquire(channelConfig.getChannelCode())) {
            saveSendRecord(dto, serialNo, channelConfig.getChannelCode(), SendStatusEnum.RATE_LIMIT, "触发通道限流", null, null);
            return new SmsSendResult(false, serialNo, null, "触发通道限流", channelConfig.getChannelCode());
        }

        SmsSignature signature = getSignature(dto.getSmsType(), channelConfig.getChannelCode());
        SmsTemplate template = getTemplate(dto.getTemplateCode(), channelConfig.getChannelCode());
        if (template == null) {
            return buildFailedResult(serialNo, channelConfig.getChannelCode(), "模板不存在");
        }

        Map<String, String> params = dto.getVariableParams();
        if (smsTypeEnum == SmsTypeEnum.VERIFICATION) {
            params = generateVerifyCodeParams(dto.getMobile(), params);
        }

        String content = renderTemplate(template.getTemplateContent(), params);

        ContentSecurityService.SecurityCheckResult securityResult = contentSecurityService.checkContent(content);
        if (!securityResult.isPassed()) {
            String hitKeywordsStr = securityResult.getHitKeywords() != null 
                ? String.join(",", securityResult.getHitKeywords()) 
                : null;
            saveSendRecord(dto, serialNo, null, SendStatusEnum.CONTENT_VIOLATION,
                    securityResult.getStatus() != null ? securityResult.getStatus().getName() : "内容违规",
                    content, params, null, null, null,
                    securityResult.getStatus() != null ? securityResult.getStatus().getCode() : 2,
                    securityResult.getRiskLevel() != null ? securityResult.getRiskLevel().getCode() : 3,
                    hitKeywordsStr, null, null, null);
            String errorMsg = "内容违规，包含敏感词: " + (hitKeywordsStr != null ? hitKeywordsStr : "未知");
            return new SmsSendResult(false, serialNo, null, errorMsg, null);
        }

        SmsProvider provider = SmsProviderFactory.getProvider(channelConfig.getChannelCode());
        if (provider == null) {
            return buildFailedResult(serialNo, channelConfig.getChannelCode(), "短信提供商不存在");
        }

        SmsSendResult result = provider.send(
                dto.getMobile(),
                signature != null ? signature.getSignatureContent() : null,
                dto.getTemplateCode(),
                template.getExternalTemplateId(),
                params,
                serialNo
        );

        MobileLocationService.MobileLocationInfo locationInfo = mobileLocationService.analyzeMobile(dto.getMobile());

        if (result.isSuccess()) {
            channelManagerService.recordSuccess(channelConfig.getChannelCode());
            saveSendRecord(dto, serialNo, channelConfig.getChannelCode(), SendStatusEnum.SUCCESS, null,
                    content, params, result.getExternalSerialNo(), signature != null ? signature.getId() : null, template.getId(),
                    securityResult.getStatus() != null ? securityResult.getStatus().getCode() : 1,
                    securityResult.getRiskLevel() != null ? securityResult.getRiskLevel().getCode() : 0,
                    null,
                    locationInfo.getProvince(), locationInfo.getCity(), locationInfo.getOperator());
        } else {
            channelManagerService.recordFail(channelConfig.getChannelCode());
            saveSendRecord(dto, serialNo, channelConfig.getChannelCode(), SendStatusEnum.FAILED,
                    result.getErrorMsg(), content, params, null, signature != null ? signature.getId() : null, template.getId(),
                    securityResult.getStatus() != null ? securityResult.getStatus().getCode() : 1,
                    securityResult.getRiskLevel() != null ? securityResult.getRiskLevel().getCode() : 0,
                    null,
                    locationInfo.getProvince(), locationInfo.getCity(), locationInfo.getOperator());

            result = tryFailover(dto, serialNo, channelConfig.getChannelCode(), content, securityResult, locationInfo);
        }

        return result;
    }

    private SmsSendResult tryFailover(SendSmsDTO dto, String serialNo, Integer failedChannelCode,
                                       String content, ContentSecurityService.SecurityCheckResult securityResult,
                                       MobileLocationService.MobileLocationInfo locationInfo) {
        log.info("尝试故障转移，原通道: {}", failedChannelCode);

        List<SmsChannelConfig> healthyChannels = channelManagerService.getHealthyChannels();
        for (SmsChannelConfig config : healthyChannels) {
            if (config.getChannelCode().equals(failedChannelCode)) {
                continue;
            }

            try {
                if (!rateLimiterService.tryAcquire(config.getChannelCode())) {
                    continue;
                }

                SmsSignature signature = getSignature(dto.getSmsType(), config.getChannelCode());
                SmsTemplate template = getTemplate(dto.getTemplateCode(), config.getChannelCode());
                if (template == null) {
                    continue;
                }

                Map<String, String> params = dto.getVariableParams();
                SmsTypeEnum smsTypeEnum = SmsTypeEnum.getByCode(dto.getSmsType());
                if (smsTypeEnum == SmsTypeEnum.VERIFICATION) {
                    String codeKey = VERIFY_CODE_KEY_PREFIX + dto.getMobile();
                    Object cachedCode = redisUtil.get(codeKey);
                    if (cachedCode != null) {
                        if (params == null) params = new HashMap<>();
                        params.put("code", cachedCode.toString());
                        params.put("expire", String.valueOf(verifyCodeExpireMinutes));
                    }
                }

                String failoverContent = renderTemplate(template.getTemplateContent(), params);

                SmsProvider provider = SmsProviderFactory.getProvider(config.getChannelCode());
                SmsSendResult result = provider.send(
                        dto.getMobile(),
                        signature != null ? signature.getSignatureContent() : null,
                        dto.getTemplateCode(),
                        template.getExternalTemplateId(),
                        params,
                        serialNo
                );

                if (result.isSuccess()) {
                    channelManagerService.recordSuccess(config.getChannelCode());
                    updateSendRecord(serialNo, config.getChannelCode(), SendStatusEnum.SUCCESS, null,
                            failoverContent, result.getExternalSerialNo(),
                            securityResult.getStatus() != null ? securityResult.getStatus().getCode() : 1,
                            securityResult.getRiskLevel() != null ? securityResult.getRiskLevel().getCode() : 0,
                            null,
                            locationInfo.getProvince(), locationInfo.getCity(), locationInfo.getOperator());
                    log.info("故障转移成功，原通道: {}, 新通道: {}", failedChannelCode, config.getChannelCode());
                    return result;
                } else {
                    channelManagerService.recordFail(config.getChannelCode());
                }
            } catch (Exception e) {
                log.error("故障转移异常，通道: {}", config.getChannelCode(), e);
            }
        }

        log.warn("所有通道都发送失败，原通道: {}", failedChannelCode);
        return new SmsSendResult(false, serialNo, null, "所有通道发送失败", null);
    }

    public boolean verifyCode(String mobile, String code) {
        if (!validateMobile(mobile) || StrUtil.isBlank(code)) {
            return false;
        }

        String key = VERIFY_CODE_KEY_PREFIX + mobile;
        Object cachedCode = redisUtil.get(key);
        if (cachedCode == null) {
            return false;
        }

        boolean valid = code.equals(cachedCode.toString());
        if (valid) {
            redisUtil.delete(key);
        }
        return valid;
    }

    private Map<String, String> generateVerifyCodeParams(String mobile, Map<String, String> existingParams) {
        Map<String, String> params = existingParams != null ? new HashMap<>(existingParams) : new HashMap<>();

        String code = RandomUtil.randomNumbers(verifyCodeLength);
        params.put("code", code);
        params.put("expire", String.valueOf(verifyCodeExpireMinutes));

        String key = VERIFY_CODE_KEY_PREFIX + mobile;
        redisUtil.set(key, code, verifyCodeExpireMinutes, TimeUnit.MINUTES);

        log.info("生成验证码, mobile={}, code={}, expire={}分钟", mobile, code, verifyCodeExpireMinutes);
        return params;
    }

    private SmsSignature getSignature(Integer smsType, Integer channelCode) {
        return signatureMapper.selectOne(
                new LambdaQueryWrapper<SmsSignature>()
                        .eq(SmsSignature::getSmsType, smsType)
                        .eq(SmsSignature::getChannelCode, channelCode)
                        .eq(SmsSignature::getStatus, 1)
                        .eq(SmsSignature::getDeleted, 0)
                        .last("LIMIT 1")
        );
    }

    private SmsTemplate getTemplate(String templateCode, Integer channelCode) {
        return templateMapper.selectOne(
                new LambdaQueryWrapper<SmsTemplate>()
                        .eq(SmsTemplate::getTemplateCode, templateCode)
                        .eq(SmsTemplate::getChannelCode, channelCode)
                        .eq(SmsTemplate::getStatus, 1)
                        .eq(SmsTemplate::getDeleted, 0)
                        .last("LIMIT 1")
        );
    }

    private String renderTemplate(String templateContent, Map<String, String> params) {
        if (StrUtil.isBlank(templateContent) || params == null || params.isEmpty()) {
            return templateContent;
        }
        String result = templateContent;
        for (Map.Entry<String, String> entry : params.entrySet()) {
            result = result.replace("${" + entry.getKey() + "}", entry.getValue());
        }
        return result;
    }

    private boolean validateMobile(String mobile) {
        if (StrUtil.isBlank(mobile)) {
            return false;
        }
        return MOBILE_PATTERN.matcher(mobile).matches();
    }

    private SmsSendResult buildFailedResult(String serialNo, Integer channelCode, String errorMsg) {
        log.error("短信发送失败: {}", errorMsg);
        return new SmsSendResult(false, serialNo, null, errorMsg, channelCode);
    }

    private void saveSendRecord(SendSmsDTO dto, String serialNo, Integer channelCode, SendStatusEnum status,
                                String errorMsg, String content, Map<String, String> params) {
        saveSendRecord(dto, serialNo, channelCode, status, errorMsg, content, params, null, null, null,
                null, null, null, null, null, null);
    }

    private void saveSendRecord(SendSmsDTO dto, String serialNo, Integer channelCode, SendStatusEnum status,
                                String errorMsg, String content, Map<String, String> params, String externalSerialNo,
                                Long signatureId, Long templateId, Integer contentSecurityStatus,
                                Integer contentSecurityRiskLevel, String contentSecurityKeywords,
                                String mobileProvince, String mobileCity, Integer mobileOperator) {
        try {
            SmsSendRecord record = new SmsSendRecord();
            record.setSerialNo(serialNo);
            record.setMobile(dto.getMobile());
            record.setSmsType(dto.getSmsType());
            record.setTemplateCode(dto.getTemplateCode());
            record.setChannelCode(channelCode);
            record.setSendContent(content);
            if (params != null) {
                record.setVariableParams(objectMapper.writeValueAsString(params));
            }
            record.setStatus(status.getCode());
            record.setErrorMsg(errorMsg);
            record.setExternalSerialNo(externalSerialNo);
            record.setSignatureId(signatureId);
            record.setTemplateId(templateId);
            record.setContentSecurityStatus(contentSecurityStatus);
            record.setContentSecurityRiskLevel(contentSecurityRiskLevel);
            record.setContentSecurityKeywords(contentSecurityKeywords);
            record.setMobileProvince(mobileProvince);
            record.setMobileCity(mobileCity);
            record.setMobileOperator(mobileOperator);
            if (status == SendStatusEnum.SUCCESS) {
                record.setSendTime(LocalDateTime.now());
                if (channelCode != null && externalSerialNo != null) {
                    receiptService.initReceiptExpireTime(record, channelCode);
                }
            }
            sendRecordMapper.insert(record);
        } catch (JsonProcessingException e) {
            log.error("保存发送记录失败，参数序列化异常", e);
        }
    }

    private void updateSendRecord(String serialNo, Integer channelCode, SendStatusEnum status,
                                  String errorMsg, String content, String externalSerialNo,
                                  Integer contentSecurityStatus, Integer contentSecurityRiskLevel,
                                  String contentSecurityKeywords, String mobileProvince,
                                  String mobileCity, Integer mobileOperator) {
        try {
            SmsSendRecord record = sendRecordMapper.selectOne(
                    new LambdaQueryWrapper<SmsSendRecord>()
                            .eq(SmsSendRecord::getSerialNo, serialNo)
            );
            if (record != null) {
                record.setChannelCode(channelCode);
                record.setStatus(status.getCode());
                record.setErrorMsg(errorMsg);
                record.setSendContent(content);
                record.setExternalSerialNo(externalSerialNo);
                if (contentSecurityStatus != null) {
                    record.setContentSecurityStatus(contentSecurityStatus);
                }
                if (contentSecurityRiskLevel != null) {
                    record.setContentSecurityRiskLevel(contentSecurityRiskLevel);
                }
                if (contentSecurityKeywords != null) {
                    record.setContentSecurityKeywords(contentSecurityKeywords);
                }
                if (mobileProvince != null) {
                    record.setMobileProvince(mobileProvince);
                }
                if (mobileCity != null) {
                    record.setMobileCity(mobileCity);
                }
                if (mobileOperator != null) {
                    record.setMobileOperator(mobileOperator);
                }
                if (status == SendStatusEnum.SUCCESS) {
                    record.setSendTime(LocalDateTime.now());
                    if (channelCode != null && externalSerialNo != null) {
                        receiptService.initReceiptExpireTime(record, channelCode);
                    }
                }
                sendRecordMapper.updateById(record);
            }
        } catch (Exception e) {
            log.error("更新发送记录失败", e);
        }
    }
}
