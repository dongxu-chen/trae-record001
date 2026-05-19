package com.payment.reconciliation.service;

import com.payment.reconciliation.dto.ReportQueryDTO;
import com.payment.reconciliation.entity.ReconciliationResult;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;

public interface ReportService {

    List<ReconciliationResult> queryReconciliationResults(ReportQueryDTO dto);

    ReconciliationResult getReconciliationResultById(Long id);

    void exportReconciliationReport(Long resultId, HttpServletResponse response) throws IOException;
}
