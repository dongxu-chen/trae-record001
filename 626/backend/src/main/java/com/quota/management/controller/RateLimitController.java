package com.quota.management.controller;

import com.quota.management.common.Result;
import com.quota.management.service.RateLimitService;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/ratelimit")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class RateLimitController {

    private final RateLimitService rateLimitService;

    @PostMapping("/check")
    public Result<RateLimitResponse> checkAndConsume(@RequestBody RateLimitRequest request) {
        RateLimitService.RateLimitResult result = rateLimitService.checkAndConsume(
                request.getTenantId(),
                request.getTokens()
        );

        RateLimitResponse response = RateLimitResponse.builder()
                .allowed(result.isAllowed())
                .reason(result.getReason())
                .granularity(result.getGranularity())
                .downgraded(result.isDowngraded())
                .delayMs(result.getDelayMs())
                .build();

        return Result.success(response);
    }

    @Data
    public static class RateLimitRequest {
        private String tenantId;
        private long tokens = 1;
    }

    @Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class RateLimitResponse {
        private boolean allowed;
        private String reason;
        private String granularity;
        private boolean downgraded;
        private long delayMs;
    }
}
