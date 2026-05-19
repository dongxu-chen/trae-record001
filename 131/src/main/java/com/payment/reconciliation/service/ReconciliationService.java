package com.payment.reconciliation.service;

import com.payment.reconciliation.dto.ReconciliationExecuteDTO;
import com.payment.reconciliation.dto.ReconciliationParseDTO;
import com.payment.reconciliation.entity.ChannelReconciliation;

public interface ReconciliationService {

    ChannelReconciliation parseReconciliationFile(ReconciliationParseDTO dto);

    void executeReconciliation(ReconciliationExecuteDTO dto);

    void processReconciliation(Long reconciliationId);
}
