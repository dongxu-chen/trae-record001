package com.sla.monitor.controller;

import com.sla.monitor.model.SlaTier;
import com.sla.monitor.service.SlaTierService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/sla-tiers")
public class SlaTierController {

    private final SlaTierService slaTierService;

    public SlaTierController(SlaTierService slaTierService) {
        this.slaTierService = slaTierService;
    }

    @GetMapping
    public List<SlaTier> getAllTiers(@RequestParam(required = false) Boolean active) {
        if (Boolean.TRUE.equals(active)) {
            return slaTierService.getActiveTiers();
        }
        return slaTierService.getAllTiers();
    }

    @GetMapping("/{id}")
    public ResponseEntity<SlaTier> getTierById(@PathVariable Long id) {
        return slaTierService.getTierById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/code/{code}")
    public ResponseEntity<SlaTier> getTierByCode(@PathVariable String code) {
        return slaTierService.getTierByCode(code)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<SlaTier> createTier(@RequestBody SlaTier tier) {
        try {
            SlaTier created = slaTierService.createTier(tier);
            return ResponseEntity.ok(created);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @PutMapping("/{id}")
    public ResponseEntity<SlaTier> updateTier(@PathVariable Long id, @RequestBody SlaTier tier) {
        try {
            SlaTier updated = slaTierService.updateTier(id, tier);
            return ResponseEntity.ok(updated);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.notFound().build();
        }
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteTier(@PathVariable Long id) {
        slaTierService.deleteTier(id);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/mine-rules")
    public ResponseEntity<String> triggerRuleMining() {
        return ResponseEntity.ok("Rule mining triggered");
    }
}
