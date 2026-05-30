package com.dtmonitor.api.controller;

import com.dtmonitor.core.model.PressureTestConfig;
import com.dtmonitor.core.model.PressureTestResult;
import com.dtmonitor.diagnosis.service.PressureTestService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/pressure-test")
@RequiredArgsConstructor
public class PressureTestController {

    private final PressureTestService pressureTestService;

    @GetMapping
    public ResponseEntity<List<PressureTestResult>> listTests() {
        return ResponseEntity.ok(pressureTestService.listAllTests());
    }

    @GetMapping("/{testId}")
    public ResponseEntity<PressureTestResult> getTest(@PathVariable String testId) {
        PressureTestResult result = pressureTestService.getTest(testId);
        if (result == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(result);
    }

    @PostMapping("/start")
    public ResponseEntity<PressureTestResult> startTest(@RequestBody PressureTestConfig config) {
        if (config.getConcurrency() <= 0 || config.getConcurrency() > 1000) {
            return ResponseEntity.badRequest().build();
        }
        if (config.getDurationSeconds() <= 0 || config.getDurationSeconds() > 3600) {
            return ResponseEntity.badRequest().build();
        }
        if (config.getFailureRate() < 0 || config.getFailureRate() > 1) {
            return ResponseEntity.badRequest().build();
        }
        if (config.getNetworkDelayMs() < 0 || config.getNetworkDelayMs() > 10000) {
            return ResponseEntity.badRequest().build();
        }
        PressureTestResult result = pressureTestService.startTest(config);
        return ResponseEntity.ok(result);
    }

    @PostMapping("/{testId}/stop")
    public ResponseEntity<PressureTestResult> stopTest(@PathVariable String testId) {
        PressureTestResult result = pressureTestService.stopTest(testId);
        if (result == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(result);
    }
}
