package com.survey.controller;

import com.survey.service.ExportService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

@RestController
@RequestMapping("/api/export")
@RequiredArgsConstructor
@Tag(name = "结果导出", description = "问卷结果导出接口")
public class ExportController {

    private final ExportService exportService;

    @GetMapping("/{surveyId}/excel")
    @Operation(summary = "导出Excel")
    public ResponseEntity<byte[]> exportToExcel(@PathVariable String surveyId) {
        byte[] excelBytes = exportService.exportToExcel(surveyId);

        String fileName = "survey_results_" + surveyId + ".xlsx";
        String encodedFileName = URLEncoder.encode(fileName, StandardCharsets.UTF_8);

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename*=UTF-8''" + encodedFileName)
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .body(excelBytes);
    }

    @GetMapping("/{surveyId}/csv")
    @Operation(summary = "导出CSV")
    public ResponseEntity<String> exportToCSV(@PathVariable String surveyId) {
        String csvContent = exportService.exportToCSV(surveyId);

        String fileName = "survey_results_" + surveyId + ".csv";
        String encodedFileName = URLEncoder.encode(fileName, StandardCharsets.UTF_8);

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename*=UTF-8''" + encodedFileName)
                .contentType(MediaType.parseMediaType("text/csv; charset=UTF-8"))
                .body("\uFEFF" + csvContent);
    }
}
