package com.survey.controller;

import com.survey.dto.RecommendRequest;
import com.survey.dto.RecommendResponse;
import com.survey.entity.SurveyTemplate;
import com.survey.service.AIRecommendService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/ai")
@RequiredArgsConstructor
@Tag(name = "AI问卷推荐", description = "智能推荐问卷模板和问题")
public class AIRecommendController {

    private final AIRecommendService aiRecommendService;

    @PostMapping("/recommend")
    @Operation(summary = "根据主题推荐问卷")
    public ResponseEntity<RecommendResponse> recommend(@Valid @RequestBody RecommendRequest request) {
        return ResponseEntity.ok(aiRecommendService.recommend(request));
    }

    @GetMapping("/templates")
    @Operation(summary = "获取所有问卷模板")
    public ResponseEntity<List<SurveyTemplate>> getAllTemplates() {
        return ResponseEntity.ok(aiRecommendService.getAllTemplates());
    }

    @GetMapping("/templates/category/{category}")
    @Operation(summary = "按分类获取模板")
    public ResponseEntity<List<SurveyTemplate>> getTemplatesByCategory(@PathVariable String category) {
        return ResponseEntity.ok(aiRecommendService.getTemplatesByCategory(category));
    }

    @PostMapping("/templates")
    @Operation(summary = "创建问卷模板")
    public ResponseEntity<SurveyTemplate> createTemplate(@RequestBody SurveyTemplate template) {
        return ResponseEntity.ok(aiRecommendService.createTemplate(template));
    }

    @PostMapping("/templates/{id}/use")
    @Operation(summary = "标记模板使用")
    public ResponseEntity<Void> useTemplate(@PathVariable String id) {
        aiRecommendService.incrementTemplateUsage(id);
        return ResponseEntity.ok().build();
    }
}
