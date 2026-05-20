package com.payment.reconciliation.service;

import com.payment.reconciliation.dto.FeeCalculateDTO;
import com.payment.reconciliation.entity.ChannelFeeConfig;
import com.payment.reconciliation.entity.TransactionFee;

import java.math.BigDecimal;
import java.util.List;

public interface ChannelFeeService {

    BigDecimal calculateFee(String channelCode, String merchantNo, BigDecimal amount);

    void calculateAndSaveBatch(FeeCalculateDTO dto);

    List<TransactionFee> getTransactionFees(String channelCode, String settlementDate);

    BigDecimal getTotalFeeByDateRange(String channelCode, String startDate, String endDate);

    List<ChannelFeeConfig> getChannelFeeConfigs(String channelCode);

    ChannelFeeConfig addChannelFeeConfig(ChannelFeeConfig config);
}
