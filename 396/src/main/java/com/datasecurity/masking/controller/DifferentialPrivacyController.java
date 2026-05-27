package com.datasecurity.masking.controller;

import com.datasecurity.masking.dp.DPQueryRequest;
import com.datasecurity.masking.dp.DPQueryResult;
import com.datasecurity.masking.dp.DifferentialPrivacyService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/dp")
public class DifferentialPrivacyController {

    @Autowired
    private DifferentialPrivacyService dpService;

    @PostMapping("/count")
    public ResponseEntity<DPQueryResult> count(@RequestBody DPQueryRequest request) {
        return ResponseEntity.ok(dpService.count(request));
    }

    @PostMapping("/sum")
    public ResponseEntity<DPQueryResult> sum(@RequestBody DPQueryRequest request) {
        return ResponseEntity.ok(dpService.sum(request));
    }

    @PostMapping("/avg")
    public ResponseEntity<DPQueryResult> average(@RequestBody DPQueryRequest request) {
        return ResponseEntity.ok(dpService.average(request));
    }

    @PostMapping("/min")
    public ResponseEntity<DPQueryResult> min(@RequestBody DPQueryRequest request) {
        return ResponseEntity.ok(dpService.min(request));
    }

    @PostMapping("/max")
    public ResponseEntity<DPQueryResult> max(@RequestBody DPQueryRequest request) {
        return ResponseEntity.ok(dpService.max(request));
    }

    @PostMapping("/histogram")
    public ResponseEntity<Map<String, DPQueryResult>> histogram(@RequestBody DPQueryRequest request) {
        return ResponseEntity.ok(dpService.histogram(request));
    }

    @PostMapping("/statistics")
    public ResponseEntity<Map<String, DPQueryResult>> statistics(@RequestBody DPQueryRequest request) {
        Map<String, DPQueryResult> stats = new HashMap<>();
        stats.put("count", dpService.count(cloneRequest(request)));
        stats.put("sum", dpService.sum(cloneRequest(request)));
        stats.put("avg", dpService.average(cloneRequest(request)));
        stats.put("min", dpService.min(cloneRequest(request)));
        stats.put("max", dpService.max(cloneRequest(request)));
        return ResponseEntity.ok(stats);
    }

    @GetMapping("/budget/{userId}")
    public ResponseEntity<Map<String, Object>> getBudget(@PathVariable String userId) {
        Map<String, Object> result = new HashMap<>();
        result.put("userId", userId);
        result.put("usedEpsilon", dpService.getUsedBudget(userId));
        result.put("totalBudget", 10.0);
        result.put("remainingBudget", 10.0 - dpService.getUsedBudget(userId));
        return ResponseEntity.ok(result);
    }

    @DeleteMapping("/budget/{userId}")
    public ResponseEntity<Void> resetBudget(@PathVariable String userId) {
        dpService.resetBudget(userId);
        return ResponseEntity.ok().build();
    }

    private DPQueryRequest cloneRequest(DPQueryRequest original) {
        return DPQueryRequest.builder()
                .databaseId(original.getDatabaseId())
                .tableName(original.getTableName())
                .columnName(original.getColumnName())
                .operation(original.getOperation())
                .epsilon(original.getEpsilon() != null ? original.getEpsilon() / 5 : 0.2)
                .delta(original.getDelta())
                .minValue(original.getMinValue())
                .maxValue(original.getMaxValue())
                .whereClause(original.getWhereClause())
                .groupBy(original.getGroupBy())
                .build();
    }
}
