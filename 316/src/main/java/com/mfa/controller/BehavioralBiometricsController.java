package com.mfa.controller;

import com.mfa.dto.BehavioralBiometrics;
import com.mfa.dto.BehavioralDataRequest;
import com.mfa.dto.BehavioralProfile;
import com.mfa.entity.User;
import com.mfa.service.BehavioralBiometricsService;
import com.mfa.service.UserService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.concurrent.TimeUnit;

@RestController
@RequestMapping("/api/behavior")
@RequiredArgsConstructor
public class BehavioralBiometricsController {

    private final BehavioralBiometricsService behavioralBiometricsService;
    private final UserService userService;
    private final RedisTemplate<String, Object> redisTemplate;

    private static final String LATEST_ANALYSIS_KEY_PREFIX = "mfa:behavior:analysis:latest:";

    @PostMapping("/collect")
    public ResponseEntity<BehavioralBiometrics> collectBehavioralData(
            @Valid @RequestBody BehavioralDataRequest request) {
        User user = userService.getCurrentUser();
        BehavioralBiometrics analysis = behavioralBiometricsService.analyzeBehavior(request, user);

        if (user != null) {
            String key = LATEST_ANALYSIS_KEY_PREFIX + user.getId();
            redisTemplate.opsForValue().set(key, analysis, 30, TimeUnit.MINUTES);
        }

        return ResponseEntity.ok(analysis);
    }

    @PostMapping("/calibrate")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Map<String, Object>> calibrateProfile(
            @Valid @RequestBody BehavioralDataRequest request) {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }

        behavioralBiometricsService.calibrateProfile(user.getId().toString(), request);

        BehavioralProfile profile = behavioralBiometricsService.getUserProfile(user.getId().toString());

        return ResponseEntity.ok(Map.of(
                "success", true,
                "sampleCount", profile != null ? profile.getSampleCount() : 0,
                "isCalibrated", profile != null && Boolean.TRUE.equals(profile.getIsCalibrated()),
                "requiredSamples", 5
        ));
    }

    @GetMapping("/profile")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<BehavioralProfile> getProfile() {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }
        BehavioralProfile profile = behavioralBiometricsService.getUserProfile(user.getId().toString());
        return ResponseEntity.ok(profile);
    }

    @GetMapping("/profile/status")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Map<String, Object>> getProfileStatus() {
        User user = userService.getCurrentUser();
        if (user == null) {
            return ResponseEntity.notFound().build();
        }

        BehavioralProfile profile = behavioralBiometricsService.getUserProfile(user.getId().toString());
        boolean isCalibrated = behavioralBiometricsService.isProfileCalibrated(user.getId().toString());

        return ResponseEntity.ok(Map.of(
                "isCalibrated", isCalibrated,
                "sampleCount", profile != null ? profile.getSampleCount() : 0,
                "requiredSamples", 5,
                "calibrated", isCalibrated
        ));
    }
}
