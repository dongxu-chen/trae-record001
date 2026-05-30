package com.ratelimit.recommender.controller;

import com.ratelimit.recommender.model.*;
import com.ratelimit.recommender.service.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/drill")
@CrossOrigin(origins = "*")
public class DrillController {

    private final RateLimitDrillService drillService;

    public DrillController(RateLimitDrillService drillService) {
        this.drillService = drillService;
    }

    @PostMapping("/start/{serviceId}")
    public ResponseEntity<RateLimitDrill> startDrill(
            @PathVariable String serviceId,
            @RequestBody(required = false) RateLimitDrill.DrillConfig config) {
        if (config == null) {
            config = drillService.createDefaultDrillConfig(serviceId);
        }
        return ResponseEntity.ok(drillService.startDrill(serviceId, config));
    }

    @GetMapping("/default-config/{serviceId}")
    public ResponseEntity<RateLimitDrill.DrillConfig> getDefaultConfig(@PathVariable String serviceId) {
        return ResponseEntity.ok(drillService.createDefaultDrillConfig(serviceId));
    }

    @GetMapping("/active")
    public ResponseEntity<List<RateLimitDrill>> getActiveDrills() {
        return ResponseEntity.ok(drillService.getActiveDrills());
    }

    @GetMapping("/completed")
    public ResponseEntity<List<RateLimitDrill>> getCompletedDrills() {
        return ResponseEntity.ok(drillService.getCompletedDrills());
    }

    @GetMapping("/{drillId}")
    public ResponseEntity<RateLimitDrill> getDrill(@PathVariable String drillId) {
        RateLimitDrill drill = drillService.getDrill(drillId);
        if (drill == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(drill);
    }

    @PostMapping("/abort/{drillId}")
    public ResponseEntity<Boolean> abortDrill(@PathVariable String drillId) {
        return ResponseEntity.ok(drillService.abortDrill(drillId));
    }
}
