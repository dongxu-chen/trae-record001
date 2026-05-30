package com.tracing.sampling.interceptor;

import com.tracing.sampling.store.SamplingConfigStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

@Component
public class LatencyStatsInterceptor implements HandlerInterceptor {

    private static final Logger logger = LoggerFactory.getLogger(LatencyStatsInterceptor.class);
    private static final String START_TIME_ATTR = "latency.startTime";
    private static final String ENDPOINT_KEY_ATTR = "latency.endpointKey";

    private final SamplingConfigStore configStore;

    public LatencyStatsInterceptor(SamplingConfigStore configStore) {
        this.configStore = configStore;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        request.setAttribute(START_TIME_ATTR, System.currentTimeMillis());
        request.setAttribute(ENDPOINT_KEY_ATTR, buildEndpointKey(request));
        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, 
                                Object handler, Exception ex) {
        try {
            Long startTime = (Long) request.getAttribute(START_TIME_ATTR);
            String endpointKey = (String) request.getAttribute(ENDPOINT_KEY_ATTR);
            
            if (startTime != null && endpointKey != null) {
                long latency = System.currentTimeMillis() - startTime;
                configStore.updateLatencyStats(endpointKey, latency);
                
                if (logger.isDebugEnabled()) {
                    logger.debug("Recorded latency for {}: {}ms", endpointKey, latency);
                }
            }
        } catch (Exception e) {
            logger.warn("Failed to record latency stats: {}", e.getMessage());
        }
    }

    private String buildEndpointKey(HttpServletRequest request) {
        String method = request.getMethod();
        String uri = request.getRequestURI();
        return method + ":" + uri;
    }
}
