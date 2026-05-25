package com.survey.controller;

import com.survey.dto.SmsCampaignRequest;
import com.survey.entity.SmsCampaign;
import com.survey.service.SmsCampaignService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/sms")
@RequiredArgsConstructor
@Tag(name = "批量投放", description = "手机号导入、短信推送问卷链接")
public class SmsCampaignController {

    private final SmsCampaignService smsCampaignService;

    @PostMapping("/campaigns")
    @Operation(summary = "创建短信投放任务")
    public ResponseEntity<SmsCampaign> createCampaign(@Valid @RequestBody SmsCampaignRequest request) {
        return ResponseEntity.ok(smsCampaignService.createCampaign(request));
    }

    @PostMapping("/campaigns/{id}/start")
    @Operation(summary = "启动短信投放任务")
    public ResponseEntity<SmsCampaign> startCampaign(@PathVariable String id) {
        return ResponseEntity.ok(smsCampaignService.startCampaign(id));
    }

    @GetMapping("/campaigns/{id}")
    @Operation(summary = "获取投放任务详情")
    public ResponseEntity<SmsCampaign> getCampaign(@PathVariable String id) {
        return ResponseEntity.ok(smsCampaignService.getCampaign(id));
    }

    @GetMapping("/campaigns/survey/{surveyId}")
    @Operation(summary = "获取问卷的所有投放任务")
    public ResponseEntity<List<SmsCampaign>> getCampaignsBySurvey(@PathVariable String surveyId) {
        return ResponseEntity.ok(smsCampaignService.getCampaignsBySurvey(surveyId));
    }

    @PostMapping("/campaigns/{id}/cancel")
    @Operation(summary = "取消投放任务")
    public ResponseEntity<Void> cancelCampaign(@PathVariable String id) {
        smsCampaignService.cancelCampaign(id);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/import")
    @Operation(summary = "导入并验证手机号列表")
    public ResponseEntity<Map<String, Object>> importPhones(@RequestBody List<String> phoneNumbers) {
        List<String> validated = smsCampaignService.importPhoneNumbers(phoneNumbers);
        return ResponseEntity.ok(Map.of(
                "validCount", validated.size(),
                "totalCount", phoneNumbers.size(),
                "phones", validated
        ));
    }
}
