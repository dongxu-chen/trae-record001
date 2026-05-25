package com.sms.platform.sdk.impl;

import com.sms.platform.common.enums.ChannelTypeEnum;
import com.sms.platform.dto.SmsSendResult;
import com.sms.platform.sdk.SmsProvider;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import cn.hutool.core.util.IdUtil;
import cn.hutool.core.util.RandomUtil;
import java.util.Map;

@Slf4j
@Component
public class TencentSmsProvider implements SmsProvider {

    @Value("${sms.tencent.enabled:true}")
    private boolean enabled;

    @Value("${sms.tencent.sign-name:【腾讯云】}")
    private String defaultSignName;

    @Override
    public String getProviderName() {
        return ChannelTypeEnum.TENCENT.getName();
    }

    @Override
    public Integer getChannelCode() {
        return ChannelTypeEnum.TENCENT.getCode();
    }

    @Override
    public SmsSendResult send(String mobile, String signName, String templateCode, String externalTemplateId, Map<String, String> params, String serialNo) {
        if (!enabled) {
            return new SmsSendResult(false, serialNo, null, "腾讯云通道已禁用", getChannelCode());
        }

        try {
            log.info("[腾讯云] 发送短信, mobile={}, signName={}, templateCode={}, externalTemplateId={}, params={}",
                    mobile, signName, templateCode, externalTemplateId, params);

            String content = buildContent(signName != null ? signName : defaultSignName, params);
            log.info("[腾讯云] 短信内容: {}", content);

            Thread.sleep(RandomUtil.randomInt(10, 50));

            if (RandomUtil.randomDouble() > 0.05) {
                String externalSerialNo = "TENCENT_" + IdUtil.fastSimpleUUID();
                log.info("[腾讯云] 短信发送成功, externalSerialNo={}", externalSerialNo);
                return new SmsSendResult(true, serialNo, externalSerialNo, null, getChannelCode());
            } else {
                log.warn("[腾讯云] 短信发送失败, 模拟运营商故障");
                return new SmsSendResult(false, serialNo, null, "模拟运营商发送失败", getChannelCode());
            }
        } catch (Exception e) {
            log.error("[腾讯云] 短信发送异常", e);
            return new SmsSendResult(false, serialNo, null, "发送异常: " + e.getMessage(), getChannelCode());
        }
    }

    @Override
    public boolean healthCheck() {
        if (!enabled) {
            return false;
        }
        try {
            Thread.sleep(RandomUtil.randomInt(5, 20));
            boolean healthy = RandomUtil.randomDouble() > 0.02;
            log.debug("[腾讯云] 健康检查结果: {}", healthy);
            return healthy;
        } catch (Exception e) {
            log.error("[腾讯云] 健康检查异常", e);
            return false;
        }
    }

    private String buildContent(String signName, Map<String, String> params) {
        StringBuilder sb = new StringBuilder(signName);
        if (params != null && !params.isEmpty()) {
            for (Map.Entry<String, String> entry : params.entrySet()) {
                sb.append(entry.getKey()).append(": ").append(entry.getValue()).append(", ");
            }
            if (sb.length() > 2) {
                sb.setLength(sb.length() - 2);
            }
        }
        return sb.toString();
    }
}
