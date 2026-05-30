package com.replay.detector.config;

import com.replay.detector.interceptor.ReplayAttackInterceptor;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
@RequiredArgsConstructor
public class WebMvcConfig implements WebMvcConfigurer {

    private final ReplayAttackInterceptor replayAttackInterceptor;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(replayAttackInterceptor)
                .addPathPatterns("/api/**")
                .excludePathPatterns("/api/replay/**");
    }
}
