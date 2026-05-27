package com.datasecurity.masking.controller;

import com.datasecurity.masking.label.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/label")
public class LabelController {

    @Autowired
    private LabelPropagationEngine propagationEngine;

    @Autowired
    private ExportFileLabeler fileLabeler;

    @GetMapping("/fields")
    public ResponseEntity<Map<String, FieldLabel>> getAllFieldLabels() {
        return ResponseEntity.ok(propagationEngine.getAllFieldLabels());
    }

    @PostMapping("/propagate")
    public ResponseEntity<Void> propagateLabel(
            @RequestParam String sourceField,
            @RequestParam String targetField) {
        propagationEngine.propagateLabel(sourceField, sourceField);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/analyze/file")
    public ResponseEntity<FileLabel> analyzeFile(@RequestParam("file") MultipartFile file) throws IOException {
        String originalFilename = file.getOriginalFilename();
        String tempPath = System.getProperty("java.io.tmpdir") + "/" + originalFilename;
        file.transferTo(new File(tempPath));

        FileLabel fileLabel;
        if (originalFilename != null && originalFilename.toLowerCase().endsWith(".csv")) {
            fileLabel = fileLabeler.analyzeCSVFile(tempPath));
        } else {
            fileLabel = fileLabeler.analyzeExcelFile(tempPath);
        }

        new File(tempPath).delete();
        return ResponseEntity.ok(fileLabel);
    }

    @PostMapping("/analyze/content")
    public ResponseEntity<FileLabel> analyzeContent(@RequestBody String content,
                                           @RequestParam(defaultValue = "CSV") String contentType) {
        return ResponseEntity.ok(fileLabeler.analyzeContent(content, contentType));
    }

    @GetMapping("/sensitivity-levels")
    public ResponseEntity<SensitivityLevel[]> getSensitivityLevels() {
        return ResponseEntity.ok(SensitivityLevel.values());
    }

    @PostMapping("/mark")
    public ResponseEntity<String> generateMark(@RequestBody FileLabel fileLabel) {
        return ResponseEntity.ok(fileLabeler.generateSensitivityMark(fileLabel));
    }
}
