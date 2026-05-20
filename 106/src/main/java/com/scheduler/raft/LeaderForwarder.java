package com.scheduler.raft;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;
import java.io.BufferedReader;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Component
public class LeaderForwarder {

    @Resource
    private RaftNode raftNode;

    @Value("${server.port}")
    private int serverPort;

    @Value("${raft.leader-forward-timeout:5000}")
    private int forwardTimeout;

    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();

    @PostConstruct
    public void init() {
        log.info("请求转发器初始化完成");
    }

    public boolean shouldForward() {
        return !raftNode.isLeader() && raftNode.getCurrentLeader() != null;
    }

    public ForwardResult forwardRequest(HttpServletRequest request, Object body) {
        if (!shouldForward()) {
            return ForwardResult.notNeeded();
        }

        String leaderAddress = raftNode.getLeaderAddress();
        if (leaderAddress == null) {
            return ForwardResult.failure("Leader地址为空");
        }

        try {
            String forwardUrl = buildForwardUrl(request, leaderAddress);
            log.info("转发请求到Leader: {} {}", request.getMethod(), forwardUrl);

            HttpHeaders headers = buildHeaders(request);
            String requestBody = body != null ? objectMapper.writeValueAsString(body) : extractRequestBody(request);

            HttpEntity<String> entity = new HttpEntity<>(requestBody, headers);
            ResponseEntity<String> response = restTemplate.exchange(
                    forwardUrl,
                    HttpMethod.resolve(request.getMethod()),
                    entity,
                    String.class
            );

            return ForwardResult.success(response.getBody(), response.getStatusCodeValue());

        } catch (Exception e) {
            log.error("转发请求失败", e);
            return ForwardResult.failure("转发请求失败: " + e.getMessage());
        }
    }

    private String buildForwardUrl(HttpServletRequest request, String leaderAddress) {
        String queryString = request.getQueryString();
        String url = "http://" + leaderAddress + request.getRequestURI();
        if (queryString != null && !queryString.isEmpty()) {
            url += "?" + queryString;
        }
        return url;
    }

    private HttpHeaders buildHeaders(HttpServletRequest request) {
        HttpHeaders headers = new HttpHeaders();
        Enumeration<String> headerNames = request.getHeaderNames();
        while (headerNames.hasMoreElements()) {
            String headerName = headerNames.nextElement();
            if (!"Content-Length".equalsIgnoreCase(headerName)) {
                headers.add(headerName, request.getHeader(headerName));
            }
        }
        headers.setContentType(MediaType.APPLICATION_JSON);
        return headers;
    }

    private String extractRequestBody(HttpServletRequest request) {
        try {
            StringBuilder sb = new StringBuilder();
            BufferedReader reader = request.getReader();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
            return sb.toString();
        } catch (Exception e) {
            return "";
        }
    }

    public static class ForwardResult {
        private final boolean forwarded;
        private final boolean success;
        private final String response;
        private final int statusCode;
        private final String message;

        private ForwardResult(boolean forwarded, boolean success, String response, int statusCode, String message) {
            this.forwarded = forwarded;
            this.success = success;
            this.response = response;
            this.statusCode = statusCode;
            this.message = message;
        }

        public static ForwardResult notNeeded() {
            return new ForwardResult(false, false, null, 0, null);
        }

        public static ForwardResult success(String response, int statusCode) {
            return new ForwardResult(true, true, response, statusCode, null);
        }

        public static ForwardResult failure(String message) {
            return new ForwardResult(true, false, null, 500, message);
        }

        public boolean isForwarded() { return forwarded; }
        public boolean isSuccess() { return success; }
        public String getResponse() { return response; }
        public int getStatusCode() { return statusCode; }
        public String getMessage() { return message; }
    }
}
