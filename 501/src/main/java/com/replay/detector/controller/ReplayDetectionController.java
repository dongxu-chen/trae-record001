package com.replay.detector.controller;

import com.replay.detector.config.ReplayDetectionProperties;
import com.replay.detector.dto.ApiResponse;
import com.replay.detector.dto.DetectionRequest;
import com.replay.detector.dto.DetectionResponse;
import com.replay.detector.model.DetectionResult;
import com.replay.detector.model.WindowStats;
import com.replay.detector.service.BloomFilterService;
import com.replay.detector.service.ReplayDetectionService;
import com.replay.detector.service.SlidingWindowService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.UUID;

@Slf4j
@RestController
@RequestMapping("/api/replay")
@RequiredArgsConstructor
public class ReplayDetectionController {

    private final ReplayDetectionService replayDetectionService;
    private final SlidingWindowService slidingWindowService;
    private final BloomFilterService bloomFilterService;
    private final ReplayDetectionProperties properties;

    @PostMapping("/detect")
    public ApiResponse<DetectionResponse> detect(@Valid @RequestBody DetectionRequest request) {
        String requestId = UUID.randomUUID().toString();
        long timestamp = request.getTimestamp() != null ? request.getTimestamp() : System.currentTimeMillis();
        String httpMethod = request.getHttpMethod() != null ? request.getHttpMethod() : "POST";

        DetectionResult result;

        if (request.getWindowSizeSeconds() != null && request.getMaxReplayCount() != null) {
            result = replayDetectionService.detectWithCustomWindow(
                    requestId, request.getPath(), request.getParams(),
                    request.getUserAgent(), request.getClientIp(), httpMethod,
                    timestamp, request.getWindowSizeSeconds(), request.getMaxReplayCount());
        } else {
            result = replayDetectionService.detect(
                    requestId, request.getPath(), request.getParams(),
                    request.getUserAgent(), request.getClientIp(), httpMethod, timestamp);
        }

        return ApiResponse.success(DetectionResponse.from(result, requestId));
    }

    @GetMapping("/stats/{fingerprintHash}")
    public ApiResponse<WindowStats> getStats(@PathVariable String fingerprintHash) {
        WindowStats stats = slidingWindowService.getStats(fingerprintHash);
        return ApiResponse.success(stats);
    }

    @DeleteMapping("/window/{fingerprintHash}")
    public ApiResponse<Void> clearWindow(@PathVariable String fingerprintHash) {
        slidingWindowService.clearWindow(fingerprintHash);
        return ApiResponse.success(null);
    }

    @PostMapping("/bloom/reset")
    public ApiResponse<Void> resetBloomFilter() {
        bloomFilterService.resetLocal();
        return ApiResponse.success(null);
    }

    @GetMapping("/config")
    public ApiResponse<ReplayDetectionProperties> getConfig() {
        return ApiResponse.success(properties);
    }
}
