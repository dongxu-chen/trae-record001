package com.security.replayguard.interceptor;

import com.security.replayguard.config.ReplayGuardProperties;
import com.security.replayguard.core.ReplayGuardManager;
import com.security.replayguard.model.RequestFeature;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class ReplayGuardInterceptor implements HandlerInterceptor {

    private final ReplayGuardManager replayGuardManager;
    private final ReplayGuardProperties properties;

    private static final String REQUEST_FEATURE_ATTR = "requestFeature";
    private static final String START_TIME_ATTR = "startTime";

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        long startTime = System.currentTimeMillis();
        request.setAttribute(START_TIME_ATTR, startTime);

        RequestFeature feature = extractFeature(request);
        request.setAttribute(REQUEST_FEATURE_ATTR, feature);

        ReplayGuardManager.DetectionResult result = replayGuardManager.checkRequest(feature);

        if (result.isBlocked()) {
            log.warn("Request blocked: reason={}, path={}, ip={}", 
                    result.getReason(), feature.getRequestPath(), feature.getIpAddress());
            
            response.setStatus(HttpServletResponse.SC_FORBIDDEN);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write(String.format("""
                    {"code": %d, "message": "%s", "reason": "%s"}
                    """, 403, "Request blocked by replay guard", result.getReason()));
            
            return false;
        }

        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) {
        Long startTime = (Long) request.getAttribute(START_TIME_ATTR);
        long duration = System.currentTimeMillis() - (startTime != null ? startTime : System.currentTimeMillis());

        RequestFeature feature = (RequestFeature) request.getAttribute(REQUEST_FEATURE_ATTR);
        if (feature != null) {
            replayGuardManager.checkRequestWithHoneypot(feature, duration);
        }
    }

    private RequestFeature extractFeature(HttpServletRequest request) {
        RequestFeature feature = new RequestFeature();

        feature.setRequestPath(request.getRequestURI());
        feature.setMethod(request.getMethod());
        feature.setIpAddress(getClientIpAddress(request));
        feature.setUserAgent(request.getHeader("User-Agent"));

        feature.setUserId(request.getHeader("X-User-Id"));
        feature.setDeviceFingerprint(request.getHeader(properties.getDeviceFingerprintHeader()));
        feature.setTimestamp(request.getHeader(properties.getTimestampHeader()));
        feature.setNonce(request.getHeader(properties.getNonceHeader()));

        feature.setQueryParams(extractQueryParams(request));

        return feature;
    }

    private Map<String, String> extractQueryParams(HttpServletRequest request) {
        Map<String, String> params = new HashMap<>();
        
        for (Map.Entry<String, String[]> entry : request.getParameterMap().entrySet()) {
            String[] values = entry.getValue();
            if (values != null && values.length > 0) {
                params.put(entry.getKey(), values[0]);
            }
        }
        
        return params;
    }

    private String getClientIpAddress(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("WL-Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("X-Real-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }

        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }

        return ip;
    }
}
