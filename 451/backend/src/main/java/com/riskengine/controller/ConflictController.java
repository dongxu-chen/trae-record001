package com.riskengine.controller;

import com.riskengine.engine.conflict.RuleConflictDetector;
import com.riskengine.model.ConflictResult;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/conflicts")
@CrossOrigin(origins = "*")
public class ConflictController {

    private final RuleConflictDetector conflictDetector;

    public ConflictController(RuleConflictDetector conflictDetector) {
        this.conflictDetector = conflictDetector;
    }

    @GetMapping("/detect")
    public ResponseEntity<List<ConflictResult>> detectConflicts() {
        return ResponseEntity.ok(conflictDetector.detectConflicts());
    }
}
