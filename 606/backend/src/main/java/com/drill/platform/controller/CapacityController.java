package com.drill.platform.controller;

import com.drill.platform.model.*;
import com.drill.platform.prediction.CapacityPredictionEngine;
import com.drill.platform.service.DrillService;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/capacity")
public class CapacityController {

    private final CapacityPredictionEngine predictionEngine;
    private final DrillService drillService;

    public CapacityController(
            CapacityPredictionEngine predictionEngine,
            DrillService drillService) {
        this.predictionEngine = predictionEngine;
        this.drillService = drillService;
    }

    @GetMapping("/predict")
    public ApiResult<CapacityPrediction> predictCapacity(
            @RequestParam(required = false, defaultValue = "default") String targetSystem,
            @RequestParam(required = false, defaultValue = "24") int horizonHours) {
        
        List<DrillTask> historicalDrills = drillService.listTasks();
        
        CapacityPrediction prediction = predictionEngine.predictCapacity(
                targetSystem, historicalDrills, horizonHours);
        
        return ApiResult.success(prediction);
    }

    @GetMapping("/watermarks")
    public ApiResult<Map<String, Double>> getWatermarkLevels(
            @RequestParam(required = false, defaultValue = "1.0") double safetyFactor) {
        
        List<DrillTask> historicalDrills = drillService.listTasks();
        
        Map<String, Double> watermarks = predictionEngine.calculateWatermarkLevels(
                historicalDrills, safetyFactor);
        
        return ApiResult.success(watermarks);
    }

    @GetMapping("/history")
    public ApiResult<List<CapacityPrediction.CapacityDataPoint>> getHistoricalCapacity(
            @RequestParam(required = false, defaultValue = "default") String targetSystem,
            @RequestParam(required = false, defaultValue = "168") int hours) {
        
        List<DrillTask> historicalDrills = drillService.listTasks();
        
        CapacityPrediction prediction = predictionEngine.predictCapacity(
                targetSystem, historicalDrills, 24);
        
        return ApiResult.success(prediction.getHistoricalData());
    }

    @GetMapping("/trend")
    public ApiResult<Map<String, Object>> getCapacityTrend(
            @RequestParam(required = false, defaultValue = "default") String targetSystem) {
        
        List<DrillTask> historicalDrills = drillService.listTasks();
        
        CapacityPrediction prediction = predictionEngine.predictCapacity(
                targetSystem, historicalDrills, 24);
        
        return ApiResult.success(prediction.getPredictionModel());
    }
}
