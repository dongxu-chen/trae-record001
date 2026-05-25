package com.survey.controller;

import com.survey.dto.SurveyCreateRequest;
import com.survey.entity.Survey;
import com.survey.service.SurveyService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/surveys")
@RequiredArgsConstructor
@Tag(name = "问卷管理", description = "问卷创建、编辑、发布、删除等接口")
public class SurveyController {

    private final SurveyService surveyService;

    @PostMapping
    @Operation(summary = "创建问卷")
    public ResponseEntity<Survey> createSurvey(@Valid @RequestBody SurveyCreateRequest request) {
        return ResponseEntity.ok(surveyService.createSurvey(request));
    }

    @PutMapping("/{id}")
    @Operation(summary = "更新问卷")
    public ResponseEntity<Survey> updateSurvey(@PathVariable String id,
                                               @Valid @RequestBody SurveyCreateRequest request) {
        return ResponseEntity.ok(surveyService.updateSurvey(id, request));
    }

    @GetMapping("/{id}")
    @Operation(summary = "获取问卷详情")
    public ResponseEntity<Survey> getSurvey(@PathVariable String id) {
        return ResponseEntity.ok(surveyService.getSurvey(id));
    }

    @GetMapping("/share/{shareCode}")
    @Operation(summary = "通过分享码获取问卷")
    public ResponseEntity<Survey> getSurveyByShareCode(@PathVariable String shareCode) {
        return ResponseEntity.ok(surveyService.getSurveyByShareCode(shareCode));
    }

    @GetMapping("/creator/{creatorId}")
    @Operation(summary = "获取创建者的问卷列表")
    public ResponseEntity<List<Survey>> getSurveysByCreator(@PathVariable String creatorId) {
        return ResponseEntity.ok(surveyService.getSurveysByCreator(creatorId));
    }

    @PostMapping("/{id}/publish")
    @Operation(summary = "发布问卷")
    public ResponseEntity<Survey> publishSurvey(@PathVariable String id) {
        return ResponseEntity.ok(surveyService.publishSurvey(id));
    }

    @PostMapping("/{id}/close")
    @Operation(summary = "关闭问卷")
    public ResponseEntity<Survey> closeSurvey(@PathVariable String id) {
        return ResponseEntity.ok(surveyService.closeSurvey(id));
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "删除问卷")
    public ResponseEntity<Void> deleteSurvey(@PathVariable String id) {
        surveyService.deleteSurvey(id);
        return ResponseEntity.noContent().build();
    }
}
