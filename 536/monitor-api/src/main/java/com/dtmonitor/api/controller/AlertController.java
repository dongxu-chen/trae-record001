package com.dtmonitor.api.controller;

import com.dtmonitor.core.model.entity.AlertRecord;
import com.dtmonitor.core.service.AlertRecordService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/alerts")
@RequiredArgsConstructor
public class AlertController {

    private final AlertRecordService alertRecordService;

    @GetMapping
    public ResponseEntity<Page<AlertRecord>> getUnacknowledged(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "triggeredAt"));
        Page<AlertRecord> result = alertRecordService.findUnacknowledged(pageable);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/transaction/{xid}")
    public ResponseEntity<Page<AlertRecord>> getByXid(
            @PathVariable String xid,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "triggeredAt"));
        Page<AlertRecord> result = alertRecordService.findByXid(xid, pageable);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/count")
    public ResponseEntity<Long> countUnacknowledged() {
        return ResponseEntity.ok(alertRecordService.countUnacknowledged());
    }

    @PutMapping("/{id}/acknowledge")
    public ResponseEntity<AlertRecord> acknowledge(
            @PathVariable Long id,
            @RequestParam String acknowledgedBy) {
        AlertRecord record = alertRecordService.acknowledge(id, acknowledgedBy);
        if (record == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(record);
    }
}
