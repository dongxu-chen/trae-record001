package com.dtmonitor.api.controller;

import com.dtmonitor.diagnosis.model.DiagnosisReport;
import com.dtmonitor.diagnosis.service.DiagnosisService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/diagnosis")
@RequiredArgsConstructor
public class DiagnosisController {

    private final DiagnosisService diagnosisService;

    @PostMapping("/{xid}")
    public ResponseEntity<DiagnosisReport> diagnose(@PathVariable String xid) {
        DiagnosisReport report = diagnosisService.diagnose(xid);
        return ResponseEntity.ok(report);
    }
}
