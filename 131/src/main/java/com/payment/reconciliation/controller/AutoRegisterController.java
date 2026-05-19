package com.payment.reconciliation.controller;

import com.payment.reconciliation.common.Result;
import com.payment.reconciliation.service.AutoRegisterService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auto-register")
public class AutoRegisterController {

    @Autowired
    private AutoRegisterService autoRegisterService;

    @PostMapping("/process-timeout")
    public Result<Void> processTimeoutDiscrepancies() {
        autoRegisterService.processTimeoutDiscrepancies();
        return Result.success();
    }
}
