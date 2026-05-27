package com.platform.points.controller;

import com.platform.points.service.PointsAnalysisService;
import com.platform.points.utils.Result;
import com.platform.points.vo.PointsLeverageVO;
import com.platform.points.vo.PointsPredictionVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/analysis")
public class PointsAnalysisController {

    @Autowired
    private PointsAnalysisService pointsAnalysisService;

    @GetMapping("/prediction/{userId}")
    public Result<PointsPredictionVO> predictPointsGrowth(
            @PathVariable Long userId,
            @RequestParam(defaultValue = "30") int days) {
        return Result.success(pointsAnalysisService.predictPointsGrowth(userId, days));
    }

    @GetMapping("/leverage")
    public Result<PointsLeverageVO> analyzePointsLeverage(
            @RequestParam String startDate,
            @RequestParam String endDate) {
        return Result.success(pointsAnalysisService.analyzePointsLeverage(startDate, endDate));
    }
}
