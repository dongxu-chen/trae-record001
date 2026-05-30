package com.distid.tracking;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Slf4j
@Configuration
public class TrackingConfig implements WebMvcConfigurer {

    private final TraceContextInterceptor traceContextInterceptor;

    public TrackingConfig(TraceContextInterceptor traceContextInterceptor) {
        this.traceContextInterceptor = traceContextInterceptor;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(traceContextInterceptor)
                .addPathPatterns("/api/**")
                .order(1);
    }

    @org.springframework.context.annotation.Bean
    public IdLifecycleTracker idLifecycleTracker(StringRedisTemplate redisTemplate,
                                                  @Value("${distid.tracking.enabled:true}") boolean enabled) {
        return new IdLifecycleTracker(redisTemplate, enabled);
    }
}
