package com.payment.reconciliation.controller;

import com.payment.reconciliation.common.Result;
import com.payment.reconciliation.dto.FundTransferDTO;
import com.payment.reconciliation.entity.FundTransfer;
import com.payment.reconciliation.service.FundTransferService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/fund-transfer")
public class FundTransferController {

    @Autowired
    private FundTransferService fundTransferService;

    @PostMapping("/create")
    public Result<FundTransfer> createFundTransfer(
            @Validated @RequestBody FundTransferDTO dto) {
        FundTransfer fundTransfer = fundTransferService.createFundTransfer(dto);
        return Result.success(fundTransfer);
    }

    @GetMapping("/list")
    public Result<List<FundTransfer>> listFundTransfers(
            @RequestParam(required = false) String channelCode,
            @RequestParam(required = false) Integer status) {
        List<FundTransfer> list = fundTransferService.listFundTransfers(channelCode, status);
        return Result.success(list);
    }

    @GetMapping("/{id}")
    public Result<FundTransfer> getFundTransferById(@PathVariable Long id) {
        FundTransfer fundTransfer = fundTransferService.getFundTransferById(id);
        return Result.success(fundTransfer);
    }
}
