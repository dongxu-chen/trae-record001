package com.ratelimit.recommender.controller;

import com.ratelimit.recommender.model.TrafficPrediction;
import com.ratelimit.recommender.service.TimeSeriesPredictionService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/prediction")
@CrossOrigin(origins = "*")
public class PredictionController {

    private final TimeSeriesPredictionService predictionService;

    public PredictionController(TimeSeriesPredictionService predictionService) {
        this.predictionService = predictionService;
    }

    @GetMapping("/traffic/{serviceId}")
    public ResponseEntity<TrafficPrediction> getTrafficPrediction(
            @PathVariable String serviceId,
            @RequestParam(defaultValue = "60") int horizonMinutes) {
        TrafficPrediction prediction = predictionService.predictTraffic(serviceId, horizonMinutes);
        return ResponseEntity.ok(prediction);
    }
}
