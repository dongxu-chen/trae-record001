package com.sms.platform.sdk;

import com.sms.platform.dto.SmsSendResult;
import java.util.Map;

public interface SmsProvider {

    String getProviderName();

    Integer getChannelCode();

    SmsSendResult send(String mobile, String signName, String templateCode, String externalTemplateId, Map<String, String> params, String serialNo);

    boolean healthCheck();
}
