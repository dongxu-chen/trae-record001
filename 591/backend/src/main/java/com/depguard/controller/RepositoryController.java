package com.depguard.controller;

import com.depguard.dto.RepositoryRequest;
import com.depguard.dto.RepositoryResponse;
import com.depguard.dto.ScanResponse;
import com.depguard.service.RepositoryService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/repositories")
@RequiredArgsConstructor
public class RepositoryController {

    private final RepositoryService repositoryService;

    @PostMapping
    public ResponseEntity<RepositoryResponse> addRepository(@RequestBody RepositoryRequest request) {
        RepositoryResponse response = repositoryService.addRepository(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping
    public ResponseEntity<List<RepositoryResponse>> getAllRepositories() {
        return ResponseEntity.ok(repositoryService.getAllRepositories());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteRepository(@PathVariable Long id) {
        repositoryService.deleteRepository(id);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/{id}/scan")
    public ResponseEntity<Map<String, String>> triggerScan(@PathVariable Long id) {
        repositoryService.triggerScan(id);
        return ResponseEntity.ok(Map.of("message", "Scan triggered for repository " + id, "status", "SCANNING"));
    }

    @GetMapping("/{id}/scans")
    public ResponseEntity<List<ScanResponse>> getScanHistory(@PathVariable Long id) {
        return ResponseEntity.ok(repositoryService.getScanHistory(id));
    }
}
