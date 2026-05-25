package com.survey.controller;

import com.survey.dto.SurveyStats;
import com.survey.service.StatsService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/stats")
@RequiredArgsConstructor
@Tag(name = "统计管理", description = "问卷结果实时统计接口")
public class StatsController {

    private final StatsService statsService;

    @GetMapping("/{surveyId}")
    @Operation(summary = "获取问卷统计结果")
    public ResponseEntity<SurveyStats> getSurveyStats(@PathVariable String surveyId) {
        return ResponseEntity.ok(statsService.getSurveyStats(surveyId));
    }
}
