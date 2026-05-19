package com.payment.reconciliation.service;

import com.payment.reconciliation.entity.Discrepancy;

import java.util.List;

public interface AutoRegisterService {

    void processTimeoutDiscrepancies();

    void autoRegisterDiscrepancy(Discrepancy discrepancy);

    void autoRegisterDiscrepancies(List<Discrepancy> discrepancies);
}
