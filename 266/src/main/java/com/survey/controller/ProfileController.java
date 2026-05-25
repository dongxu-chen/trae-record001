package com.survey.controller;

import com.survey.dto.RespondentProfile;
import com.survey.service.ProfileAnalysisService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/profile")
@RequiredArgsConstructor
@Tag(name = "答题者画像分析", description = "答题时段、设备分布、完成率等画像分析")
public class ProfileController {

    private final ProfileAnalysisService profileAnalysisService;

    @GetMapping("/{surveyId}")
    @Operation(summary = "获取问卷答题者画像分析")
    public ResponseEntity<RespondentProfile> getRespondentProfile(@PathVariable String surveyId) {
        return ResponseEntity.ok(profileAnalysisService.analyzeRespondentProfile(surveyId));
    }
}
