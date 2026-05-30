package com.tracing.sampling.config;

import com.tracing.sampling.interceptor.LatencyStatsInterceptor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    private final LatencyStatsInterceptor latencyStatsInterceptor;

    public WebMvcConfig(LatencyStatsInterceptor latencyStatsInterceptor) {
        this.latencyStatsInterceptor = latencyStatsInterceptor;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(latencyStatsInterceptor)
                .addPathPatterns("/**")
                .excludePathPatterns("/actuator/**", "/health", "/metrics");
    }
}
