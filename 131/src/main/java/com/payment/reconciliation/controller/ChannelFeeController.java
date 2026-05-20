package com.payment.reconciliation.controller;

import com.payment.reconciliation.common.Result;
import com.payment.reconciliation.dto.FeeCalculateDTO;
import com.payment.reconciliation.entity.ChannelFeeConfig;
import com.payment.reconciliation.entity.TransactionFee;
import com.payment.reconciliation.service.ChannelFeeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;

@RestController
@RequestMapping("/api/channel-fee")
public class ChannelFeeController {

    @Autowired
    private ChannelFeeService channelFeeService;

    @GetMapping("/calculate")
    public Result<BigDecimal> calculateFee(
            @RequestParam String channelCode,
            @RequestParam(required = false) String merchantNo,
            @RequestParam BigDecimal amount) {
        BigDecimal fee = channelFeeService.calculateFee(channelCode, merchantNo, amount);
        return Result.success(fee);
    }

    @PostMapping("/calculate-batch")
    public Result<Void> calculateAndSaveBatch(@RequestBody FeeCalculateDTO dto) {
        channelFeeService.calculateAndSaveBatch(dto);
        return Result.success();
    }

    @GetMapping("/list")
    public Result<List<TransactionFee>> getTransactionFees(
            @RequestParam String channelCode,
            @RequestParam String settlementDate) {
        List<TransactionFee> list = channelFeeService.getTransactionFees(channelCode, settlementDate);
        return Result.success(list);
    }

    @GetMapping("/total")
    public Result<BigDecimal> getTotalFeeByDateRange(
            @RequestParam String channelCode,
            @RequestParam String startDate,
            @RequestParam String endDate) {
        BigDecimal total = channelFeeService.getTotalFeeByDateRange(channelCode, startDate, endDate);
        return Result.success(total);
    }

    @GetMapping("/configs/{channelCode}")
    public Result<List<ChannelFeeConfig>> getChannelFeeConfigs(@PathVariable String channelCode) {
        List<ChannelFeeConfig> list = channelFeeService.getChannelFeeConfigs(channelCode);
        return Result.success(list);
    }

    @PostMapping("/config")
    public Result<ChannelFeeConfig> addChannelFeeConfig(@RequestBody ChannelFeeConfig config) {
        ChannelFeeConfig result = channelFeeService.addChannelFeeConfig(config);
        return Result.success(result);
    }
}
