package com.payment.reconciliation.controller;

import com.payment.reconciliation.common.Result;
import com.payment.reconciliation.dto.ReconciliationExecuteDTO;
import com.payment.reconciliation.dto.ReconciliationParseDTO;
import com.payment.reconciliation.entity.ChannelReconciliation;
import com.payment.reconciliation.service.ReconciliationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/reconciliation")
public class ReconciliationController {

    @Autowired
    private ReconciliationService reconciliationService;

    @PostMapping("/parse")
    public Result<ChannelReconciliation> parseReconciliationFile(
            @Validated @RequestBody ReconciliationParseDTO dto) {
        ChannelReconciliation result = reconciliationService.parseReconciliationFile(dto);
        return Result.success(result);
    }

    @PostMapping("/execute")
    public Result<Void> executeReconciliation(
            @Validated @RequestBody ReconciliationExecuteDTO dto) {
        reconciliationService.executeReconciliation(dto);
        return Result.success();
    }

    @PostMapping("/process/{id}")
    public Result<Void> processReconciliation(@PathVariable Long id) {
        reconciliationService.processReconciliation(id);
        return Result.success();
    }
}
