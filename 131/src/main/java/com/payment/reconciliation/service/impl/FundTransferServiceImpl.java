package com.payment.reconciliation.service.impl;

import cn.hutool.core.util.IdUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.payment.reconciliation.dto.FundTransferDTO;
import com.payment.reconciliation.entity.FundTransfer;
import com.payment.reconciliation.entity.TransactionLog;
import com.payment.reconciliation.enums.BusinessTypeEnum;
import com.payment.reconciliation.enums.TransactionStatusEnum;
import com.payment.reconciliation.mapper.FundTransferMapper;
import com.payment.reconciliation.mapper.TransactionLogMapper;
import com.payment.reconciliation.service.FundTransferService;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.core.RocketMQTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
public class FundTransferServiceImpl implements FundTransferService {

    @Autowired
    private FundTransferMapper fundTransferMapper;

    @Autowired
    private TransactionLogMapper transactionLogMapper;

    @Autowired
    private RocketMQTemplate rocketMQTemplate;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public FundTransfer createFundTransfer(FundTransferDTO dto) {
        log.info("创建资金调拨, requestId: {}, channelCode: {}", dto.getRequestId(), dto.getChannelCode());

        FundTransfer existing = fundTransferMapper.selectByRequestId(dto.getRequestId());
        if (existing != null) {
            log.warn("重复请求，直接返回已存在的调拨记录, requestId: {}", dto.getRequestId());
            return existing;
        }

        String transactionId = IdUtil.simpleUUID();

        TransactionLog transactionLog = new TransactionLog();
        transactionLog.setTransactionId(transactionId);
        transactionLog.setBusinessType(BusinessTypeEnum.FUND_TRANSFER.getCode());
        transactionLog.setStatus(TransactionStatusEnum.PENDING.getCode());
        transactionLog.setRetryCount(0);
        transactionLog.setCreateTime(LocalDateTime.now());
        transactionLog.setUpdateTime(LocalDateTime.now());
        transactionLogMapper.insert(transactionLog);

        FundTransfer fundTransfer = new FundTransfer();
        fundTransfer.setTransferNo(IdUtil.simpleUUID());
        fundTransfer.setRequestId(dto.getRequestId());
        fundTransfer.setDiscrepancyId(dto.getDiscrepancyId());
        fundTransfer.setChannelCode(dto.getChannelCode());
        fundTransfer.setTransferType(dto.getTransferType());
        fundTransfer.setAmount(dto.getAmount());
        fundTransfer.setFromAccount(dto.getFromAccount());
        fundTransfer.setToAccount(dto.getToAccount());
        fundTransfer.setStatus(0);
        fundTransfer.setRemark(dto.getRemark());
        fundTransfer.setOperator(dto.getOperator());
        fundTransfer.setCreateTime(LocalDateTime.now());
        fundTransfer.setUpdateTime(LocalDateTime.now());
        fundTransferMapper.insert(fundTransfer);

        rocketMQTemplate.sendMessageInTransaction(
                "fund-transfer-topic",
                MessageBuilder.withPayload(fundTransfer.getId())
                        .setHeader("TRANSACTION_ID", transactionId)
                        .setHeader("BUSINESS_TYPE", BusinessTypeEnum.FUND_TRANSFER.getCode())
                        .setHeader("BUSINESS_ID", String.valueOf(fundTransfer.getId()))
                        .build(),
                null
        );

        log.info("资金调拨创建成功, transferNo: {}", fundTransfer.getTransferNo());
        return fundTransfer;
    }

    @Override
    public List<FundTransfer> listFundTransfers(String channelCode, Integer status) {
        LambdaQueryWrapper<FundTransfer> wrapper = new LambdaQueryWrapper<>();
        if (channelCode != null) {
            wrapper.eq(FundTransfer::getChannelCode, channelCode);
        }
        if (status != null) {
            wrapper.eq(FundTransfer::getStatus, status);
        }
        wrapper.orderByDesc(FundTransfer::getCreateTime);
        return fundTransferMapper.selectList(wrapper);
    }

    @Override
    public FundTransfer getFundTransferById(Long id) {
        return fundTransferMapper.selectById(id);
    }
}
