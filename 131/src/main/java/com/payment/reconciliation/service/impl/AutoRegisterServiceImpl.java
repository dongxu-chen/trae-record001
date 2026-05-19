package com.payment.reconciliation.service.impl;

import cn.hutool.core.util.IdUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.payment.reconciliation.entity.Discrepancy;
import com.payment.reconciliation.entity.Transaction;
import com.payment.reconciliation.enums.DiscrepancyTypeEnum;
import com.payment.reconciliation.mapper.DiscrepancyMapper;
import com.payment.reconciliation.mapper.TransactionMapper;
import com.payment.reconciliation.service.AutoRegisterService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
public class AutoRegisterServiceImpl implements AutoRegisterService {

    @Autowired
    private DiscrepancyMapper discrepancyMapper;

    @Autowired
    private TransactionMapper transactionMapper;

    @Value("${reconciliation.auto-register-timeout-minutes:1440}")
    private int autoRegisterTimeoutMinutes;

    @Override
    @Scheduled(fixedDelay = 300000)
    public void processTimeoutDiscrepancies() {
        log.info("开始处理超时未处理的对账差异");

        LocalDateTime timeoutTime = LocalDateTime.now().minusMinutes(autoRegisterTimeoutMinutes);

        LambdaQueryWrapper<Discrepancy> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Discrepancy::getStatus, 0)
                .le(Discrepancy::getCreateTime, timeoutTime);

        List<Discrepancy> discrepancies = discrepancyMapper.selectList(wrapper);

        if (!discrepancies.isEmpty()) {
            log.info("发现{}笔超时未处理的对账差异，开始自动补登", discrepancies.size());
            autoRegisterDiscrepancies(discrepancies);
        }

        log.info("超时对账差异处理完成");
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void autoRegisterDiscrepancy(Discrepancy discrepancy) {
        log.info("开始自动补登对账差异，差异ID: {}, 订单号: {}", discrepancy.getId(), discrepancy.getOrderNo());

        if (DiscrepancyTypeEnum.LONG.getCode().equals(discrepancy.getType())) {
            Transaction transaction = new Transaction();
            transaction.setTransactionNo(IdUtil.simpleUUID());
            transaction.setOrderNo(discrepancy.getOrderNo());
            transaction.setChannelCode(discrepancy.getChannelCode());
            transaction.setMerchantNo(discrepancy.getOrderNo().substring(0, Math.min(8, discrepancy.getOrderNo().length())));
            transaction.setAmount(discrepancy.getChannelAmount());
            transaction.setFee(BigDecimal.ZERO);
            transaction.setStatus(1);
            transaction.setTransTime(LocalDateTime.now());
            transaction.setCreateTime(LocalDateTime.now());
            transaction.setUpdateTime(LocalDateTime.now());
            transactionMapper.insert(transaction);

            log.info("长款自动补登完成，交易号: {}", transaction.getTransactionNo());
        } else if (DiscrepancyTypeEnum.SHORT.getCode().equals(discrepancy.getType())) {
            LambdaQueryWrapper<Transaction> wrapper = new LambdaQueryWrapper<>();
            wrapper.eq(Transaction::getOrderNo, discrepancy.getOrderNo());
            Transaction transaction = transactionMapper.selectOne(wrapper);

            if (transaction != null) {
                transaction.setStatus(0);
                transaction.setUpdateTime(LocalDateTime.now());
                transactionMapper.updateById(transaction);
                log.info("短款自动冲正完成，交易号: {}", transaction.getTransactionNo());
            }
        } else if (DiscrepancyTypeEnum.AMOUNT_MISMATCH.getCode().equals(discrepancy.getType())) {
            LambdaQueryWrapper<Transaction> wrapper = new LambdaQueryWrapper<>();
            wrapper.eq(Transaction::getOrderNo, discrepancy.getOrderNo());
            Transaction transaction = transactionMapper.selectOne(wrapper);

            if (transaction != null) {
                transaction.setAmount(discrepancy.getChannelAmount());
                transaction.setUpdateTime(LocalDateTime.now());
                transactionMapper.updateById(transaction);
                log.info("金额不符自动调整完成，交易号: {}", transaction.getTransactionNo());
            }
        }

        discrepancy.setStatus(2);
        discrepancy.setHandleRemark("系统自动补登处理");
        discrepancy.setHandler("SYSTEM");
        discrepancy.setHandleTime(LocalDateTime.now());
        discrepancy.setUpdateTime(LocalDateTime.now());
        discrepancyMapper.updateById(discrepancy);

        log.info("对账差异自动补登完成，差异ID: {}", discrepancy.getId());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void autoRegisterDiscrepancies(List<Discrepancy> discrepancies) {
        for (Discrepancy discrepancy : discrepancies) {
            try {
                autoRegisterDiscrepancy(discrepancy);
            } catch (Exception e) {
                log.error("自动补登失败，差异ID: {}", discrepancy.getId(), e);
            }
        }
    }
}
