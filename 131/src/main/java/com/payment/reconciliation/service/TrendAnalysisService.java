package com.payment.reconciliation.service;

import com.payment.reconciliation.dto.TrendAnalysisDTO;
import com.payment.reconciliation.entity.DiscrepancyTrend;

import java.util.List;
import java.util.Map;

public interface TrendAnalysisService {

    void generateDailyTrendStatistics();

    List<DiscrepancyTrend> getTrendData(TrendAnalysisDTO dto);

    Map<String, Object> getTrendChartData(TrendAnalysisDTO dto);

    Map<String, Object> getDiscrepancyTypeDistribution(TrendAnalysisDTO dto);
}
