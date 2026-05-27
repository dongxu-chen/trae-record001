package com.datasecurity.masking.controller;

import com.datasecurity.masking.model.DatabaseConfig;
import com.datasecurity.masking.model.SensitiveField;
import com.datasecurity.masking.service.DataMaskingService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/masking")
public class DataMaskingController {

    @Autowired
    private DataMaskingService dataMaskingService;

    @PostMapping("/scan")
    public ResponseEntity<List<SensitiveField>> scanDatabase(@RequestBody DatabaseConfig config) {
        List<SensitiveField> fields = dataMaskingService.scanDatabase(config);
        return ResponseEntity.ok(fields);
    }

    @PostMapping("/mask/result")
    public ResponseEntity<List<Map<String, Object>>> maskResult(
            @RequestBody List<Map<String, Object>> result,
            @RequestParam String databaseId) {
        List<Map<String, Object>> maskedResult = dataMaskingService.maskQueryResult(result, databaseId);
        return ResponseEntity.ok(maskedResult);
    }

    @PostMapping("/mask/row")
    public ResponseEntity<Map<String, Object>> maskRow(
            @RequestBody Map<String, Object> row,
            @RequestParam String databaseId) {
        Map<String, Object> maskedRow = dataMaskingService.maskRow(row, databaseId);
        return ResponseEntity.ok(maskedRow);
    }

    @GetMapping("/fields/{databaseId}")
    public ResponseEntity<List<SensitiveField>> getSensitiveFields(@PathVariable String databaseId) {
        List<SensitiveField> fields = dataMaskingService.getSensitiveFields(databaseId);
        if (fields == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(fields);
    }
}
