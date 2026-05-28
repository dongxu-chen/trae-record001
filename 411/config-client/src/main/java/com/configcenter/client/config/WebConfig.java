package com.configcenter.client.config;

import com.configcenter.client.interceptor.RequestTrackingInterceptor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    private final RequestTrackingInterceptor requestTrackingInterceptor;

    public WebConfig(RequestTrackingInterceptor requestTrackingInterceptor) {
        this.requestTrackingInterceptor = requestTrackingInterceptor;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(requestTrackingInterceptor)
                .addPathPatterns("/**")
                .excludePathPatterns("/actuator/**");
    }
}
