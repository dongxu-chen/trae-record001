package com.payment.reconciliation.service;

import com.payment.reconciliation.dto.TrendAnalysisDTO;
import com.payment.reconciliation.entity.SettlementMonitor;

import java.util.List;

public interface SettlementMonitorService {

    void monitorSettlementDelay();

    void createSettlementMonitor(String channelCode);

    List<SettlementMonitor> getDelayedSettlements(Integer alertLevel);

    List<SettlementMonitor> getSettlementHistory(TrendAnalysisDTO dto);

    void confirmSettlementArrival(Long monitorId);
}
