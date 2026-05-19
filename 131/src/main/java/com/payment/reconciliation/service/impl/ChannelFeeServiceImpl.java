package com.payment.reconciliation.service.impl;

import cn.hutool.core.util.IdUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.payment.reconciliation.dto.FeeCalculateDTO;
import com.payment.reconciliation.entity.ChannelFeeConfig;
import com.payment.reconciliation.entity.Transaction;
import com.payment.reconciliation.entity.TransactionFee;
import com.payment.reconciliation.enums.FeeTypeEnum;
import com.payment.reconciliation.mapper.ChannelFeeConfigMapper;
import com.payment.reconciliation.mapper.TransactionFeeMapper;
import com.payment.reconciliation.mapper.TransactionMapper;
import com.payment.reconciliation.service.ChannelFeeService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Service
public class ChannelFeeServiceImpl implements ChannelFeeService {

    @Autowired
    private ChannelFeeConfigMapper channelFeeConfigMapper;

    @Autowired
    private TransactionFeeMapper transactionFeeMapper;

    @Autowired
    private TransactionMapper transactionMapper;

    @Override
    public BigDecimal calculateFee(String channelCode, String merchantNo, BigDecimal amount) {
        ChannelFeeConfig config = channelFeeConfigMapper.selectMatchedConfig(channelCode, merchantNo, amount);

        if (config == null) {
            log.warn("未找到匹配的费率配置，channelCode: {}, merchantNo: {}, amount: {}", channelCode, merchantNo, amount);
            return BigDecimal.ZERO;
        }

        BigDecimal feeAmount = BigDecimal.ZERO;

        if (FeeTypeEnum.PERCENTAGE.getCode().equals(config.getFeeType())) {
            feeAmount = amount.multiply(config.getFeeRate()).setScale(2, RoundingMode.HALF_UP);
        } else if (FeeTypeEnum.FIXED.getCode().equals(config.getFeeType())) {
            feeAmount = config.getFixedFee();
        } else if (FeeTypeEnum.TIERED.getCode().equals(config.getFeeType())) {
            feeAmount = amount.multiply(config.getFeeRate()).setScale(2, RoundingMode.HALF_UP);
        }

        if (config.getMinFee() != null && feeAmount.compareTo(config.getMinFee()) < 0) {
            feeAmount = config.getMinFee();
        }
        if (config.getMaxFee() != null && feeAmount.compareTo(config.getMaxFee()) > 0) {
            feeAmount = config.getMaxFee();
        }

        return feeAmount;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void calculateAndSaveBatch(FeeCalculateDTO dto) {
        log.info("开始批量计算手续费，渠道: {}, 结算日期: {}", dto.getChannelCode(), dto.getSettlementDate());

        LambdaQueryWrapper<Transaction> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Transaction::getChannelCode, dto.getChannelCode());
        wrapper.apply("DATE(trans_time) = {0}", dto.getSettlementDate().toString());

        List<Transaction> transactions = transactionMapper.selectList(wrapper);
        log.info("查询到{}笔交易需要计算手续费", transactions.size());

        List<TransactionFee> feeList = new ArrayList<>();
        for (Transaction transaction : transactions) {
            TransactionFee fee = calculateTransactionFee(transaction, dto.getSettlementDate());
            feeList.add(fee);
        }

        if (!feeList.isEmpty()) {
            int batchSize = 1000;
            for (int i = 0; i < feeList.size(); i += batchSize) {
                int end = Math.min(i + batchSize, feeList.size());
                List<TransactionFee> batch = feeList.subList(i, end);
                transactionFeeMapper.batchInsert(batch);
            }
        }

        log.info("手续费计算完成，共处理{}笔记录", feeList.size());
    }

    private TransactionFee calculateTransactionFee(Transaction transaction, LocalDate settlementDate) {
        BigDecimal feeAmount = calculateFee(transaction.getChannelCode(), transaction.getMerchantNo(), transaction.getAmount());

        TransactionFee fee = new TransactionFee();
        fee.setFeeNo(IdUtil.simpleUUID());
        fee.setChannelCode(transaction.getChannelCode());
        fee.setMerchantNo(transaction.getMerchantNo());
        fee.setTransactionNo(transaction.getTransactionNo());
        fee.setOrderNo(transaction.getOrderNo());
        fee.setSettlementDate(settlementDate);
        fee.setTransAmount(transaction.getAmount());
        fee.setFeeAmount(feeAmount);
        fee.setFeeRate(BigDecimal.ZERO);
        fee.setFeeType(1);
        fee.setStatus(1);
        fee.setCreateTime(LocalDateTime.now());
        fee.setUpdateTime(LocalDateTime.now());

        return fee;
    }

    @Override
    public List<TransactionFee> getTransactionFees(String channelCode, String settlementDate) {
        LocalDate date = LocalDate.parse(settlementDate, DateTimeFormatter.ISO_DATE);
        return transactionFeeMapper.selectBySettlementDate(channelCode, date);
    }

    @Override
    public BigDecimal getTotalFeeByDateRange(String channelCode, String startDate, String endDate) {
        LocalDate start = LocalDate.parse(startDate, DateTimeFormatter.ISO_DATE);
        LocalDate end = LocalDate.parse(endDate, DateTimeFormatter.ISO_DATE);
        return transactionFeeMapper.sumFeeByDateRange(channelCode, start, end);
    }

    @Override
    public List<ChannelFeeConfig> getChannelFeeConfigs(String channelCode) {
        LambdaQueryWrapper<ChannelFeeConfig> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ChannelFeeConfig::getChannelCode, channelCode)
                .eq(ChannelFeeConfig::getStatus, 1);
        return channelFeeConfigMapper.selectList(wrapper);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ChannelFeeConfig addChannelFeeConfig(ChannelFeeConfig config) {
        log.info("添加渠道费率配置，channelCode: {}, feeType: {}", config.getChannelCode(), config.getFeeType());

        config.setCreateTime(LocalDateTime.now());
        config.setUpdateTime(LocalDateTime.now());
        channelFeeConfigMapper.insert(config);

        log.info("渠道费率配置添加成功，ID: {}", config.getId());
        return config;
    }
}
