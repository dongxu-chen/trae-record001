package com.coupon.controller;

import com.coupon.common.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.Map;

@RestController
@RequestMapping("/health")
public class HealthController {

    @GetMapping
    public ApiResponse<Map<String, Object>> health() {
        return ApiResponse.success(Map.of(
                "status", "UP",
                "timestamp", LocalDateTime.now().toString(),
                "service", "coupon-intelligent-system",
                "version", "1.0.0"
        ));
    }

    @GetMapping("/ping")
    public String ping() {
        return "pong";
    }
}
