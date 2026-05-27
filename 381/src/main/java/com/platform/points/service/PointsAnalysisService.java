package com.platform.points.service;

import com.platform.points.vo.PointsLeverageVO;
import com.platform.points.vo.PointsPredictionVO;

public interface PointsAnalysisService {

    PointsPredictionVO predictPointsGrowth(Long userId, int days);

    PointsLeverageVO analyzePointsLeverage(String startDate, String endDate);
}
