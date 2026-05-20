package com.econtract.service;

import com.aliyun.dysmsapi20170525.Client;
import com.aliyun.dysmsapi20170525.models.SendSmsRequest;
import com.aliyun.dysmsapi20170525.models.SendSmsResponse;
import com.aliyun.teaopenapi.models.Config;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.econtract.common.BusinessException;
import com.econtract.common.ResultCode;
import com.econtract.entity.SmsCode;
import com.econtract.mapper.SmsCodeMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.time.LocalDateTime;
import java.util.Random;

@Slf4j
@Service
public class SmsService {

    @Value("${sms.aliyun.access-key-id}")
    private String accessKeyId;

    @Value("${sms.aliyun.access-key-secret}")
    private String accessKeySecret;

    @Value("${sms.aliyun.region-id}")
    private String regionId;

    @Value("${sms.aliyun.sign-name}")
    private String signName;

    @Value("${sms.aliyun.template-code}")
    private String templateCode;

    @Resource
    private SmsCodeMapper smsCodeMapper;

    public void sendSms(String phone, String bizType) {
        String code = generateCode();
        try {
            Client client = createClient();
            SendSmsRequest sendSmsRequest = new SendSmsRequest()
                    .setPhoneNumbers(phone)
                    .setSignName(signName)
                    .setTemplateCode(templateCode)
                    .setTemplateParam("{\"code\":\"" + code + "\"}");
            SendSmsResponse response = client.sendSms(sendSmsRequest);
            log.info("短信发送响应: {}", response);
            if (!"OK".equals(response.getBody().getCode())) {
                throw new BusinessException(ResultCode.SMS_SEND_FAIL);
            }
            saveSmsCode(phone, code, bizType);
        } catch (BusinessException e) {
            throw e;
        } catch (Exception e) {
            log.error("短信发送失败: {}", e.getMessage(), e);
            saveSmsCode(phone, code, bizType);
        }
    }

    public boolean verifyCode(String phone, String code, String bizType) {
        QueryWrapper<SmsCode> wrapper = new QueryWrapper<>();
        wrapper.eq("phone", phone)
                .eq("biz_type", bizType)
                .eq("used", 0)
                .orderByDesc("create_time")
                .last("limit 1");
        SmsCode smsCode = smsCodeMapper.selectOne(wrapper);
        if (smsCode == null) {
            throw new BusinessException(ResultCode.SMS_CODE_ERROR);
        }
        if (smsCode.getExpireTime().isBefore(LocalDateTime.now())) {
            throw new BusinessException(ResultCode.SMS_CODE_EXPIRED);
        }
        if (!smsCode.getCode().equals(code)) {
            throw new BusinessException(ResultCode.SMS_CODE_ERROR);
        }
        smsCode.setUsed(1);
        smsCodeMapper.updateById(smsCode);
        return true;
    }

    private String generateCode() {
        Random random = new Random();
        return String.format("%06d", random.nextInt(1000000));
    }

    private void saveSmsCode(String phone, String code, String bizType) {
        SmsCode smsCode = new SmsCode();
        smsCode.setPhone(phone);
        smsCode.setCode(code);
        smsCode.setBizType(bizType);
        smsCode.setExpireTime(LocalDateTime.now().plusMinutes(5));
        smsCode.setUsed(0);
        smsCode.setCreateTime(LocalDateTime.now());
        smsCodeMapper.insert(smsCode);
    }

    private Client createClient() throws Exception {
        Config config = new Config()
                .setAccessKeyId(accessKeyId)
                .setAccessKeySecret(accessKeySecret);
        config.endpoint = "dysmsapi.aliyuncs.com";
        return new Client(config);
    }
}
