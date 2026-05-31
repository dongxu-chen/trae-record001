package com.dlq.platform.api.controller;

import com.dlq.platform.api.common.Result;
import com.dlq.platform.analysis.service.DeadLetterAnalysisService;
import com.dlq.platform.common.dto.DeadLetterAnalysisResult;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.es.service.DeadLetterEsService;
import jakarta.validation.constraints.NotEmpty;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/analysis")
@RequiredArgsConstructor
public class AnalysisController {

    private final DeadLetterAnalysisService analysisService;
    private final DeadLetterEsService deadLetterEsService;

    @PostMapping("/analyze")
    public Result<DeadLetterAnalysisResult> analyze(
            @RequestParam String id,
            @RequestParam(required = false, defaultValue = "false") Boolean deepAnalysis) {
        DeadLetterMessage message = deadLetterEsService.findById(id);
        if (message == null) {
            return Result.fail("消息不存在");
        }
        DeadLetterAnalysisResult result = analysisService.analyze(message);
        return Result.success(result);
    }

    @PostMapping("/batch-analyze")
    public Result<List<DeadLetterAnalysisResult>> batchAnalyze(
            @RequestBody @NotEmpty(message = "消息ID列表不能为空") List<String> ids,
            @RequestParam(required = false, defaultValue = "false") Boolean deepAnalysis) {
        List<DeadLetterMessage> messages = deadLetterEsService.findByIds(ids);
        List<DeadLetterAnalysisResult> results = analysisService.analyzeBatch(messages);
        return Result.success(results);
    }

    @GetMapping("/suggestions/{id}")
    public Result<Map<String, Object>> suggestions(@PathVariable String id) {
        DeadLetterMessage message = deadLetterEsService.findById(id);
        if (message == null) {
            return Result.fail("消息不存在");
        }
        DeadLetterAnalysisResult analysis = analysisService.analyze(message);

        Map<String, Object> suggestions = new HashMap<>();
        suggestions.put("analysis", analysis);

        List<Map<String, Object>> suggestionList = new ArrayList<>();

        if (analysis != null && analysis.getRepairSteps() != null) {
            for (int i = 0; i < analysis.getRepairSteps().size(); i++) {
                Map<String, Object> step = new HashMap<>();
                step.put("order", i + 1);
                step.put("action", analysis.getRepairSteps().get(i));
                step.put("type", getStepType(i, analysis.getRepairSteps().size()));
                suggestionList.add(step);
            }
        }

        suggestions.put("steps", suggestionList);
        suggestions.put("suggestedAction", analysis != null ? analysis.getSuggestedAction() : null);
        suggestions.put("confidence", analysis != null ? analysis.getConfidence() : 0);
        suggestions.put("deadReasonType", analysis != null ? analysis.getDeadReasonType() : null);

        return Result.success(suggestions);
    }

    private String getStepType(int index, int total) {
        if (index == 0) return "INITIAL";
        if (index == total - 1) return "FINAL";
        return "PROCESS";
    }
}
