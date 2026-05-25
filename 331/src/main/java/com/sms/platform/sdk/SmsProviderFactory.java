package com.sms.platform.sdk;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeansException;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;
import org.springframework.stereotype.Component;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Component
public class SmsProviderFactory implements ApplicationContextAware {

    private static final Map<Integer, SmsProvider> PROVIDER_MAP = new HashMap<>();

    @Override
    public void setApplicationContext(ApplicationContext applicationContext) throws BeansException {
        Map<String, SmsProvider> providers = applicationContext.getBeansOfType(SmsProvider.class);
        for (SmsProvider provider : providers.values()) {
            PROVIDER_MAP.put(provider.getChannelCode(), provider);
            log.info("注册短信提供商: {} - {}", provider.getChannelCode(), provider.getProviderName());
        }
    }

    public static SmsProvider getProvider(Integer channelCode) {
        return PROVIDER_MAP.get(channelCode);
    }

    public static Map<Integer, SmsProvider> getAllProviders() {
        return new HashMap<>(PROVIDER_MAP);
    }
}
