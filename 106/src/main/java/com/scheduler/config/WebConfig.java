package com.scheduler.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import javax.annotation.Resource;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Resource
    private LeaderForwardInterceptor leaderForwardInterceptor;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(leaderForwardInterceptor)
                .addPathPatterns("/api/job/**")
                .excludePathPatterns("/api/cluster/**", "/actuator/**");
    }
}
