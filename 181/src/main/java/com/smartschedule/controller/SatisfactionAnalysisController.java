package com.smartschedule.controller;

import com.smartschedule.dto.ApiResponse;
import com.smartschedule.dto.ScheduleSatisfactionAnalysis;
import com.smartschedule.service.SatisfactionAnalysisService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/analysis")
@CrossOrigin(origins = "*")
public class SatisfactionAnalysisController {

    @Autowired
    private SatisfactionAnalysisService satisfactionAnalysisService;

    @GetMapping("/schedule/{scheduleId}/satisfaction")
    public ResponseEntity<ApiResponse<ScheduleSatisfactionAnalysis>> analyzeScheduleSatisfaction(
            @PathVariable Long scheduleId) {
        ScheduleSatisfactionAnalysis analysis = satisfactionAnalysisService.analyzeSchedule(scheduleId);
        return ResponseEntity.ok(ApiResponse.success(analysis));
    }
}
