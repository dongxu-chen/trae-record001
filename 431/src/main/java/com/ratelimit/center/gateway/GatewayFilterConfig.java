package com.ratelimit.center.gateway;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.servlet.DispatcherType;

@Slf4j
@Configuration
@ConditionalOnProperty(name = "rate-limit.gateway.enabled", havingValue = "true", matchIfMissing = true)
public class GatewayFilterConfig {

    @Bean
    public FilterRegistrationBean<GatewayRateLimitFilter> gatewayRateLimitFilterRegistration(GatewayRateLimitFilter filter) {
        log.info("Registering GatewayRateLimitFilter");
        FilterRegistrationBean<GatewayRateLimitFilter> registration = new FilterRegistrationBean<>();
        registration.setFilter(filter);
        registration.addUrlPatterns("/*");
        registration.setName("gatewayRateLimitFilter");
        registration.setOrder(1);
        registration.setDispatcherTypes(DispatcherType.REQUEST);
        return registration;
    }
}
