package com.payment.reconciliation.service;

import com.payment.reconciliation.dto.DiscrepancyHandleDTO;
import com.payment.reconciliation.entity.Discrepancy;

import java.util.List;

public interface DiscrepancyService {

    List<Discrepancy> listDiscrepancies(String channelCode, Integer type, Integer status);

    Discrepancy getDiscrepancyById(Long id);

    void handleDiscrepancy(DiscrepancyHandleDTO dto);
}
