package com.example.deduplication.core;

import com.example.deduplication.config.DeduplicationProperties;
import com.google.common.hash.Hashing;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.util.MultiValueMap;
import org.springframework.util.StringUtils;

import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Component
@RequiredArgsConstructor
public class RequestHashGenerator {

    private final DeduplicationProperties properties;

    public String generateHash(ServerHttpRequest request, String body) {
        StringBuilder sb = new StringBuilder();

        String userId = request.getHeaders().getFirst(properties.getUserIdHeader());
        if (!StringUtils.hasText(userId)) {
            userId = "anonymous";
        }
        sb.append("userId:").append(userId).append("|");

        sb.append("method:").append(request.getMethod()).append("|");
        sb.append("path:").append(request.getPath().value()).append("|");

        if (properties.isIncludeQueryParams()) {
            String queryParams = buildQueryParams(request);
            sb.append("query:").append(queryParams).append("|");
        }

        if (properties.getIncludeHeaders() != null && !properties.getIncludeHeaders().isEmpty()) {
            String headers = buildHeaders(request.getHeaders());
            sb.append("headers:").append(headers).append("|");
        }

        if (properties.isIncludeBody() && StringUtils.hasText(body)) {
            sb.append("body:").append(body);
        }

        String rawString = sb.toString();
        String hash = Hashing.sha256()
                .hashString(rawString, StandardCharsets.UTF_8)
                .toString();

        log.debug("Generated request hash: {} for raw string: {}", hash,
                rawString.length() > 200 ? rawString.substring(0, 200) + "..." : rawString);

        return hash;
    }

    private String buildQueryParams(ServerHttpRequest request) {
        MultiValueMap<String, String> queryParams = request.getQueryParams();
        if (queryParams.isEmpty()) {
            return "";
        }

        TreeMap<String, List<String>> sortedParams = new TreeMap<>(queryParams);
        return sortedParams.entrySet().stream()
                .map(entry -> entry.getKey() + "=" + String.join(",", entry.getValue()))
                .collect(Collectors.joining("&"));
    }

    private String buildHeaders(HttpHeaders httpHeaders) {
        List<String> headersToInclude = properties.getIncludeHeaders();
        if (headersToInclude == null || headersToInclude.isEmpty()) {
            return "";
        }

        TreeMap<String, String> sortedHeaders = new TreeMap<>();
        for (String headerName : headersToInclude) {
            String headerValue = httpHeaders.getFirst(headerName);
            if (headerValue != null) {
                sortedHeaders.put(headerName, headerValue);
            }
        }

        return sortedHeaders.entrySet().stream()
                .map(entry -> entry.getKey() + "=" + entry.getValue())
                .collect(Collectors.joining(";"));
    }
}
