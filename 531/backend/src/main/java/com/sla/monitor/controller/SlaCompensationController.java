package com.sla.monitor.controller;

import com.sla.monitor.model.SlaCompensation;
import com.sla.monitor.service.SlaCompensationService;
import com.sla.monitor.repository.ServiceInfoRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/compensations")
public class SlaCompensationController {

    private final SlaCompensationService compensationService;
    private final ServiceInfoRepository serviceInfoRepository;

    public SlaCompensationController(SlaCompensationService compensationService,
                                      ServiceInfoRepository serviceInfoRepository) {
        this.compensationService = compensationService;
        this.serviceInfoRepository = serviceInfoRepository;
    }

    @GetMapping
    public List<SlaCompensation> getAllCompensations(
            @RequestParam(required = false) String serviceName,
            @RequestParam(required = false, defaultValue = "30") int days) {
        if (serviceName != null) {
            return compensationService.getCompensationsForService(serviceName);
        }
        return compensationService.getRecentCompensations(days);
    }

    @GetMapping("/pending")
    public List<SlaCompensation> getPendingCompensations() {
        return compensationService.getPendingCompensations();
    }

    @GetMapping("/{id}")
    public ResponseEntity<SlaCompensation> getCompensationById(@PathVariable Long id) {
        return compensationService.getCompensationRepository().findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/check/{serviceName}")
    public ResponseEntity<SlaCompensation> checkAndGenerate(@PathVariable String serviceName) {
        return serviceInfoRepository.findByServiceName(serviceName)
                .map(service -> {
                    SlaCompensation compensation = compensationService.checkAndGenerateCompensation(service);
                    if (compensation != null) {
                        return ResponseEntity.ok(compensation);
                    }
                    return ResponseEntity.noContent().build();
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/approve")
    public ResponseEntity<SlaCompensation> approveCompensation(
            @PathVariable Long id,
            @RequestBody Map<String, String> request) {
        String approvedBy = request.getOrDefault("approvedBy", "system");
        SlaCompensation compensation = compensationService.approveCompensation(id, approvedBy);
        if (compensation != null) {
            return ResponseEntity.ok(compensation);
        }
        return ResponseEntity.notFound().build();
    }

    @PostMapping("/{id}/resolve")
    public ResponseEntity<SlaCompensation> resolveCompensation(@PathVariable Long id) {
        SlaCompensation compensation = compensationService.resolveCompensation(id);
        if (compensation != null) {
            return ResponseEntity.ok(compensation);
        }
        return ResponseEntity.notFound().build();
    }

    @PostMapping("/manual")
    public ResponseEntity<SlaCompensation> generateManualCompensation(
            @RequestBody Map<String, Object> request) {
        String serviceName = (String) request.get("serviceName");
        String severityStr = (String) request.get("severity");
        String reason = (String) request.get("reason");

        if (serviceName == null || severityStr == null) {
            return ResponseEntity.badRequest().build();
        }

        SlaCompensation.ViolationSeverity severity = 
            SlaCompensation.ViolationSeverity.valueOf(severityStr.toUpperCase());

        SlaCompensation compensation = 
            compensationService.generateManualCompensation(serviceName, severity, reason);
        
        if (compensation != null) {
            return ResponseEntity.ok(compensation);
        }
        return ResponseEntity.notFound().build();
    }

    @GetMapping("/statistics")
    public ResponseEntity<Map<String, Object>> getCompensationStatistics() {
        List<SlaCompensation> allCompensations = compensationService.getRecentCompensations(30);
        long pendingCount = compensationService.getPendingCompensations().size();
        long approvedCount = allCompensations.stream().filter(c -> Boolean.TRUE.equals(c.getApproved())).count();
        long criticalCount = allCompensations.stream()
                .filter(c -> c.getViolationSeverity() == SlaCompensation.ViolationSeverity.CRITICAL)
                .count();
        long severeCount = allCompensations.stream()
                .filter(c -> c.getViolationSeverity() == SlaCompensation.ViolationSeverity.SEVERE)
                .count();

        double totalCreditPercent = allCompensations.stream()
                .mapToDouble(c -> c.getCreditPercent() != null ? c.getCreditPercent() : 0)
                .sum();

        return ResponseEntity.ok(Map.of(
            "totalCompensations", allCompensations.size(),
            "pendingCompensations", pendingCount,
            "approvedCompensations", approvedCount,
            "criticalViolations", criticalCount,
            "severeViolations", severeCount,
            "totalCreditPercent", totalCreditPercent
        ));
    }
}
