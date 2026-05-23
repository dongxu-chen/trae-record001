package com.emailmarketing.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.emailmarketing.common.Result;
import com.emailmarketing.entity.AbTest;
import com.emailmarketing.entity.AbTestVariant;
import com.emailmarketing.service.AbTestService;
import com.emailmarketing.service.AbTestVariantService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/ab-tests")
public class AbTestController {

    @Autowired
    private AbTestService abTestService;

    @Autowired
    private AbTestVariantService variantService;

    @GetMapping
    public Result<Page<AbTest>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) Integer status) {
        return Result.success(abTestService.listTests(page, size, name, status));
    }

    @GetMapping("/{id}")
    public Result<Map<String, Object>> getById(@PathVariable Long id) {
        return Result.success(abTestService.getTestResults(id));
    }

    @PostMapping
    public Result<Void> create(@RequestBody Map<String, Object> request) {
        AbTest test = new AbTest();
        test.setName((String) request.get("name"));
        test.setTemplateId(Long.valueOf(request.get("templateId").toString()));
        test.setGroupId(Long.valueOf(request.get("groupId").toString()));
        test.setTestType(Integer.valueOf(request.get("testType").toString()));
        test.setSampleSize(request.get("sampleSize") != null ? Integer.parseInt(request.get("sampleSize").toString()) : 100);
        test.setMetricType(request.get("metricType") != null ? Integer.parseInt(request.get("metricType").toString()) : 1);

        List<Map<String, Object>> variantsData = (List<Map<String, Object>>) request.get("variants");
        List<AbTestVariant> variants = variantsData.stream().map(v -> {
            AbTestVariant variant = new AbTestVariant();
            variant.setVariantName((String) v.get("variantName"));
            variant.setSubject((String) v.get("subject"));
            variant.setContent((String) v.get("content"));
            variant.setWeight(v.get("weight") != null ? Integer.parseInt(v.get("weight").toString()) : 1);
            return variant;
        }).toList();

        boolean success = abTestService.createTest(test, variants);
        return success ? Result.success() : Result.error("创建失败");
    }

    @PostMapping("/{id}/start")
    public Result<Void> startTest(@PathVariable Long id) {
        boolean success = abTestService.startTest(id);
        return success ? Result.success() : Result.error("启动失败");
    }

    @PostMapping("/{id}/determine-winner")
    public Result<AbTestVariant> determineWinner(@PathVariable Long id) {
        AbTestVariant winner = abTestService.determineWinner(id);
        return winner != null ? Result.success(winner) : Result.error("无法确定胜出变体");
    }

    @PostMapping("/{id}/launch-winner")
    public Result<Void> launchWinner(@PathVariable Long id) {
        boolean success = abTestService.launchWinner(id);
        return success ? Result.success() : Result.error("启动失败");
    }

    @GetMapping("/{id}/variants")
    public Result<List<AbTestVariant>> getVariants(@PathVariable Long id) {
        return Result.success(variantService.getVariantsByTestId(id));
    }
}
