package com.mfa.controller;

import com.mfa.dto.AuthHealthDashboard;
import com.mfa.dto.AuthMethodStats;
import com.mfa.service.AuthHealthService;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api/admin/health")
@RequiredArgsConstructor
@PreAuthorize("hasRole('ADMIN')")
public class AuthHealthController {

    private final AuthHealthService authHealthService;

    @GetMapping("/dashboard")
    public ResponseEntity<AuthHealthDashboard> getDashboard() {
        AuthHealthDashboard dashboard = authHealthService.getDashboard();
        return ResponseEntity.ok(dashboard);
    }

    @GetMapping("/dashboard/range")
    public ResponseEntity<AuthHealthDashboard> getDashboardForDateRange(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate) {
        AuthHealthDashboard dashboard = authHealthService.getDashboardForDateRange(startDate, endDate);
        return ResponseEntity.ok(dashboard);
    }

    @GetMapping("/methods")
    public ResponseEntity<List<AuthMethodStats>> getAuthMethodStats(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate) {
        if (startDate == null) {
            startDate = LocalDate.now().minusDays(6);
        }
        if (endDate == null) {
            endDate = LocalDate.now();
        }
        List<AuthMethodStats> stats = authHealthService.getAuthMethodStats(startDate, endDate);
        return ResponseEntity.ok(stats);
    }
}
