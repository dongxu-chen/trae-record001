package com.replay.detector.interceptor;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.replay.detector.model.DetectionResult;
import com.replay.detector.service.ReplayDetectionService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.util.Enumeration;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Component
@RequiredArgsConstructor
public class ReplayAttackInterceptor implements HandlerInterceptor {

    private final ReplayDetectionService replayDetectionService;
    private final ObjectMapper objectMapper;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String requestId = extractRequestId(request);
        String path = request.getRequestURI();
        Map<String, String> params = extractParams(request);
        String userAgent = request.getHeader("User-Agent");
        String clientIp = extractClientIp(request);
        String httpMethod = request.getMethod();
        long timestamp = extractTimestamp(request);

        DetectionResult result = replayDetectionService.detect(
                requestId, path, params, userAgent, clientIp, httpMethod, timestamp);

        if (result.isReplay()) {
            log.warn("Blocking replay attack: hash={}, path={}, clientIp={}, replayCount={}",
                    result.getFingerprintHash(), path, clientIp, result.getReplayCount());

            response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            response.setHeader("X-Replay-Detected", "true");
            response.setHeader("X-Replay-Hash", result.getFingerprintHash());

            Map<String, Object> body = new HashMap<>();
            body.put("error", "Replay attack detected");
            body.put("replayCount", result.getReplayCount());
            body.put("fingerprintHash", result.getFingerprintHash());
            body.put("message", result.getMessage());
            body.put("requestId", requestId);

            response.getWriter().write(objectMapper.writeValueAsString(body));
            return false;
        }

        request.setAttribute("replayDetectionResult", result);
        request.setAttribute("requestId", requestId);
        return true;
    }

    private String extractRequestId(HttpServletRequest request) {
        String id = request.getHeader("X-Request-Id");
        return id != null ? id : UUID.randomUUID().toString();
    }

    private Map<String, String> extractParams(HttpServletRequest request) {
        Map<String, String> params = new HashMap<>();
        Enumeration<String> paramNames = request.getParameterNames();
        while (paramNames.hasMoreElements()) {
            String name = paramNames.nextElement();
            params.put(name, request.getParameter(name));
        }
        return params;
    }

    private String extractClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty()) {
            ip = request.getHeader("X-Real-IP");
        }
        if (ip == null || ip.isEmpty()) {
            ip = request.getRemoteAddr();
        }
        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }
        return ip;
    }

    private long extractTimestamp(HttpServletRequest request) {
        String ts = request.getHeader("X-Timestamp");
        if (ts != null) {
            try {
                return Long.parseLong(ts);
            } catch (NumberFormatException e) {
                log.debug("Invalid timestamp header: {}", ts);
            }
        }
        return System.currentTimeMillis();
    }
}
