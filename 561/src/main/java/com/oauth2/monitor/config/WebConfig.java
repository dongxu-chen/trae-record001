package com.oauth2.monitor.config;

import com.oauth2.monitor.monitor.OAuth2MetricsInterceptor;
import com.oauth2.monitor.tracing.TraceIdFilter;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.Ordered;

@Configuration
public class WebConfig {

    @Bean
    public FilterRegistrationBean<TraceIdFilter> traceIdFilterRegistration(TraceIdFilter traceIdFilter) {
        FilterRegistrationBean<TraceIdFilter> registration = new FilterRegistrationBean<>();
        registration.setFilter(traceIdFilter);
        registration.addUrlPatterns("/*");
        registration.setName("traceIdFilter");
        registration.setOrder(Ordered.HIGHEST_PRECEDENCE);
        return registration;
    }

    @Bean
    public FilterRegistrationBean<OAuth2MetricsInterceptor> metricsInterceptorRegistration(
            OAuth2MetricsInterceptor metricsInterceptor) {
        FilterRegistrationBean<OAuth2MetricsInterceptor> registration = new FilterRegistrationBean<>();
        registration.setFilter(metricsInterceptor);
        registration.addUrlPatterns("/oauth2/*");
        registration.setName("oauth2MetricsInterceptor");
        registration.setOrder(Ordered.HIGHEST_PRECEDENCE + 1);
        return registration;
    }
}
