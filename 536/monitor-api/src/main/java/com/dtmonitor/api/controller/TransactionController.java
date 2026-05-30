package com.dtmonitor.api.controller;

import com.dtmonitor.core.enums.TransactionMode;
import com.dtmonitor.core.enums.TransactionStatus;
import com.dtmonitor.core.model.entity.BranchTransaction;
import com.dtmonitor.core.model.entity.GlobalTransaction;
import com.dtmonitor.core.model.entity.TransactionEvent;
import com.dtmonitor.core.service.BranchTransactionService;
import com.dtmonitor.core.service.GlobalTransactionService;
import com.dtmonitor.core.service.TransactionEventService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/transactions")
@RequiredArgsConstructor
public class TransactionController {

    private final GlobalTransactionService globalTransactionService;
    private final BranchTransactionService branchTransactionService;
    private final TransactionEventService transactionEventService;

    @GetMapping
    public ResponseEntity<Page<GlobalTransaction>> search(
            @RequestParam(required = false) TransactionMode mode,
            @RequestParam(required = false) TransactionStatus status,
            @RequestParam(required = false) String applicationId,
            @RequestParam(required = false) String trafficColor,
            @RequestParam(required = false) String businessType,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime startTime,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime endTime,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "beginTime"));
        Page<GlobalTransaction> result = globalTransactionService.search(mode, status, applicationId, trafficColor, businessType, startTime, endTime, pageable);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/traffic-colors")
    public ResponseEntity<List<String>> getTrafficColors() {
        return ResponseEntity.ok(globalTransactionService.findDistinctTrafficColors());
    }

    @GetMapping("/business-types")
    public ResponseEntity<List<String>> getBusinessTypes() {
        return ResponseEntity.ok(globalTransactionService.findDistinctBusinessTypes());
    }

    @PutMapping("/{xid}/traffic-info")
    public ResponseEntity<GlobalTransaction> updateTrafficInfo(
            @PathVariable String xid,
            @RequestBody Map<String, Object> request) {
        String trafficColor = (String) request.get("trafficColor");
        String businessType = (String) request.get("businessType");
        @SuppressWarnings("unchecked")
        Map<String, String> tags = (Map<String, String>) request.get("tags");
        GlobalTransaction tx = globalTransactionService.updateTrafficInfo(xid, trafficColor, businessType, tags);
        if (tx == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(tx);
    }

    @GetMapping("/{xid}")
    public ResponseEntity<GlobalTransaction> getById(@PathVariable String xid) {
        GlobalTransaction tx = globalTransactionService.findById(xid);
        if (tx == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(tx);
    }

    @GetMapping("/{xid}/branches")
    public ResponseEntity<List<BranchTransaction>> getBranches(@PathVariable String xid) {
        List<BranchTransaction> branches = branchTransactionService.findByXid(xid);
        return ResponseEntity.ok(branches);
    }

    @GetMapping("/{xid}/events")
    public ResponseEntity<List<TransactionEvent>> getEvents(@PathVariable String xid) {
        List<TransactionEvent> events = transactionEventService.findByXid(xid);
        return ResponseEntity.ok(events);
    }

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("byStatus", globalTransactionService.countByStatus());
        stats.put("byMode", globalTransactionService.countByMode());
        stats.put("activeCount", globalTransactionService.countActive());
        stats.put("lastHourCount", globalTransactionService.countTotalSince(LocalDateTime.now().minusHours(1)));
        return ResponseEntity.ok(stats);
    }
}
