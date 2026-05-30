package com.apiversion.compare.controller;

import com.apiversion.compare.dto.CompatibilityReport;
import com.apiversion.compare.dto.DiffRequest;
import com.apiversion.compare.dto.DiffResponse;
import com.apiversion.compare.entity.DiffResult;
import com.apiversion.compare.mapper.DiffResultMapper;
import com.apiversion.compare.service.CompatibilityService;
import com.apiversion.compare.service.CompareService;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1")
@RequiredArgsConstructor
@Tag(name = "版本对比", description = "OpenAPI版本差异对比、兼容性检测接口")
public class CompareController {

    private final CompareService compareService;
    private final CompatibilityService compatibilityService;
    private final DiffResultMapper diffResultMapper;

    @PostMapping("/diff")
    @Operation(summary = "对比OpenAPI文档差异", description = "传入两个OpenAPI 3.0文档JSON，对比差异")
    public DiffResponse diff(@RequestBody DiffRequest request) {
        return compareService.compareOpenApi(request);
    }

    @GetMapping("/diff/versions")
    @Operation(summary = "对比两个版本差异", description = "根据版本ID对比数据库中存储的两个API版本差异")
    public DiffResponse diffVersions(
            @Parameter(description = "源版本ID", required = true) @RequestParam Long sourceVersionId,
            @Parameter(description = "目标版本ID", required = true) @RequestParam Long targetVersionId) {
        return compareService.compareVersions(sourceVersionId, targetVersionId);
    }

    @PostMapping("/diff/json")
    @Operation(summary = "对比OpenAPI JSON差异", description = "直接传入两个OpenAPI JSON字符串进行对比")
    public DiffResponse diffJson(
            @Parameter(description = "源版本OpenAPI JSON", required = true) @RequestParam String sourceOpenApi,
            @Parameter(description = "目标版本OpenAPI JSON", required = true) @RequestParam String targetOpenApi) {
        return compareService.compareOpenApiJson(sourceOpenApi, targetOpenApi);
    }

    @GetMapping("/compatibility")
    @Operation(summary = "检测版本兼容性", description = "检测两个版本之间的兼容性，生成兼容性报告")
    public CompatibilityReport checkCompatibility(
            @Parameter(description = "源版本ID", required = true) @RequestParam Long sourceVersionId,
            @Parameter(description = "目标版本ID", required = true) @RequestParam Long targetVersionId) {
        return compatibilityService.checkCompatibility(sourceVersionId, targetVersionId);
    }

    @GetMapping("/reports")
    @Operation(summary = "查询对比报告列表", description = "分页查询历史对比报告")
    public Page<DiffResult> getReports(
            @Parameter(description = "源版本ID") @RequestParam(required = false) Long sourceVersionId,
            @Parameter(description = "目标版本ID") @RequestParam(required = false) Long targetVersionId,
            @Parameter(description = "是否兼容") @RequestParam(required = false) Boolean compatible,
            @Parameter(description = "页码", defaultValue = "1") @RequestParam(defaultValue = "1") Integer page,
            @Parameter(description = "每页大小", defaultValue = "20") @RequestParam(defaultValue = "20") Integer size) {

        QueryWrapper<DiffResult> wrapper = new QueryWrapper<>();
        if (sourceVersionId != null) {
            wrapper.eq("source_version_id", sourceVersionId);
        }
        if (targetVersionId != null) {
            wrapper.eq("target_version_id", targetVersionId);
        }
        if (compatible != null) {
            wrapper.eq("compatible", compatible);
        }
        wrapper.orderByDesc("create_time");

        return diffResultMapper.selectPage(new Page<>(page, size), wrapper);
    }

    @GetMapping("/reports/{id}")
    @Operation(summary = "查询对比报告详情", description = "根据报告ID查询详细的对比结果")
    public DiffResult getReportById(@Parameter(description = "报告ID") @PathVariable Long id) {
        return diffResultMapper.selectById(id);
    }

    @GetMapping("/reports/versions")
    @Operation(summary = "查询版本对比历史", description = "查询两个版本之间的所有对比记录")
    public List<DiffResult> getReportsByVersions(
            @Parameter(description = "源版本ID", required = true) @RequestParam Long sourceVersionId,
            @Parameter(description = "目标版本ID", required = true) @RequestParam Long targetVersionId) {

        QueryWrapper<DiffResult> wrapper = new QueryWrapper<>();
        wrapper.eq("source_version_id", sourceVersionId);
        wrapper.eq("target_version_id", targetVersionId);
        wrapper.orderByDesc("create_time");

        return diffResultMapper.selectList(wrapper);
    }

    @DeleteMapping("/reports/{id}")
    @Operation(summary = "删除对比报告", description = "根据ID删除对比报告")
    public void deleteReport(@Parameter(description = "报告ID") @PathVariable Long id) {
        diffResultMapper.deleteById(id);
    }
}
