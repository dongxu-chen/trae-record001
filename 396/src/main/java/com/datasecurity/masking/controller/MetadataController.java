package com.datasecurity.masking.controller;

import com.datasecurity.masking.model.DatabaseConfig;
import com.datasecurity.masking.model.SensitiveField;
import com.datasecurity.masking.service.MetadataService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/metadata")
public class MetadataController {

    @Autowired
    private MetadataService metadataService;

    @PostMapping("/scan")
    public ResponseEntity<List<SensitiveField>> scanDatabase(@RequestBody DatabaseConfig config) {
        List<SensitiveField> fields = metadataService.scanDatabase(config);
        return ResponseEntity.ok(fields);
    }

    @GetMapping("/{databaseId}")
    public ResponseEntity<List<SensitiveField>> getSensitiveFields(@PathVariable String databaseId) {
        List<SensitiveField> fields = metadataService.getSensitiveFields(databaseId);
        if (fields == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(fields);
    }

    @PostMapping("/refresh")
    public ResponseEntity<Void> refreshMetadata(@RequestBody DatabaseConfig config) {
        metadataService.refreshMetadata(config);
        return ResponseEntity.ok().build();
    }
}
