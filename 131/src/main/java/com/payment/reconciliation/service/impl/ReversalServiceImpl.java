package com.payment.reconciliation.service.impl;

import cn.hutool.core.util.IdUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.payment.reconciliation.entity.Discrepancy;
import com.payment.reconciliation.entity.ReversalTask;
import com.payment.reconciliation.entity.Transaction;
import com.payment.reconciliation.enums.DiscrepancyTypeEnum;
import com.payment.reconciliation.mapper.DiscrepancyMapper;
import com.payment.reconciliation.mapper.ReversalTaskMapper;
import com.payment.reconciliation.mapper.TransactionMapper;
import com.payment.reconciliation.service.ReversalService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
public class ReversalServiceImpl implements ReversalService {

    @Autowired
    private ReversalTaskMapper reversalTaskMapper;

    @Autowired
    private DiscrepancyMapper discrepancyMapper;

    @Autowired
    private TransactionMapper transactionMapper;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ReversalTask createReversalTask(Discrepancy discrepancy) {
        log.info("创建自动冲正任务, discrepancyId: {}", discrepancy.getId());

        ReversalTask task = new ReversalTask();
        task.setTaskNo(IdUtil.simpleUUID());
        task.setDiscrepancyId(discrepancy.getId());
        task.setChannelCode(discrepancy.getChannelCode());
        task.setOrderNo(discrepancy.getOrderNo());
        task.setStatus(0);
        task.setRetryCount(0);
        task.setMaxRetry(3);
        task.setCreateTime(LocalDateTime.now());
        task.setUpdateTime(LocalDateTime.now());

        if (DiscrepancyTypeEnum.LONG.getCode().equals(discrepancy.getType())) {
            task.setTaskType(1);
            task.setAmount(discrepancy.getDifferenceAmount());
        } else if (DiscrepancyTypeEnum.SHORT.getCode().equals(discrepancy.getType())) {
            task.setTaskType(2);
            task.setAmount(discrepancy.getDifferenceAmount());
        } else {
            task.setTaskType(3);
            task.setAmount(discrepancy.getDifferenceAmount());
        }

        reversalTaskMapper.insert(task);
        log.info("自动冲正任务创建成功, taskNo: {}", task.getTaskNo());
        return task;
    }

    @Override
    @Scheduled(fixedDelay = 60000)
    public void processReversalTasks() {
        log.debug("开始扫描待处理的冲正任务");

        List<ReversalTask> tasks = reversalTaskMapper.selectPendingTasks(0, 10);

        for (ReversalTask task : tasks) {
            try {
                executeReversalTask(task);
            } catch (Exception e) {
                log.error("执行冲正任务失败, taskId: {}", task.getId(), e);
                handleTaskFailure(task, e);
            }
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void executeReversalTask(ReversalTask task) {
        log.info("执行冲正任务, taskId: {}, taskType: {}", task.getId(), task.getTaskType());

        task.setStatus(1);
        task.setUpdateTime(LocalDateTime.now());
        reversalTaskMapper.updateById(task);

        Discrepancy discrepancy = discrepancyMapper.selectById(task.getDiscrepancyId());
        if (discrepancy == null) {
            throw new RuntimeException("差错记录不存在");
        }

        switch (task.getTaskType()) {
            case 1:
                handleLongReversal(task, discrepancy);
                break;
            case 2:
                handleShortReversal(task, discrepancy);
                break;
            case 3:
                handleAmountAdjustment(task, discrepancy);
                break;
            default:
                throw new RuntimeException("未知的冲正任务类型");
        }

        task.setStatus(2);
        task.setHandleTime(LocalDateTime.now());
        task.setUpdateTime(LocalDateTime.now());
        reversalTaskMapper.updateById(task);

        discrepancy.setStatus(2);
        discrepancy.setHandleTime(LocalDateTime.now());
        discrepancy.setHandler("SYSTEM");
        discrepancy.setUpdateTime(LocalDateTime.now());
        discrepancyMapper.updateById(discrepancy);

        log.info("冲正任务执行成功, taskId: {}", task.getId());
    }

    private void handleLongReversal(ReversalTask task, Discrepancy discrepancy) {
        log.info("处理长款补登, orderNo: {}, amount: {}", discrepancy.getOrderNo(), task.getAmount());

        Transaction transaction = new Transaction();
        transaction.setTransactionNo(IdUtil.simpleUUID());
        transaction.setOrderNo(discrepancy.getOrderNo());
        transaction.setChannelCode(discrepancy.getChannelCode());
        transaction.setAmount(discrepancy.getChannelAmount());
        transaction.setFee(BigDecimal.ZERO);
        transaction.setStatus(1);
        transaction.setTransTime(LocalDateTime.now());
        transaction.setCreateTime(LocalDateTime.now());
        transaction.setUpdateTime(LocalDateTime.now());
        transactionMapper.insert(transaction);

        task.setErrorMsg("长款补登完成");
    }

    private void handleShortReversal(ReversalTask task, Discrepancy discrepancy) {
        log.info("处理短款冲正, orderNo: {}, amount: {}", discrepancy.getOrderNo(), task.getAmount());

        LambdaQueryWrapper<Transaction> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Transaction::getOrderNo, discrepancy.getOrderNo());
        Transaction transaction = transactionMapper.selectOne(wrapper);

        if (transaction != null) {
            transaction.setStatus(0);
            transaction.setUpdateTime(LocalDateTime.now());
            transactionMapper.updateById(transaction);
            task.setErrorMsg("短款冲正完成，交易已标记作废");
        } else {
            task.setErrorMsg("短款冲正警告：未找到对应的交易记录");
        }
    }

    private void handleAmountAdjustment(ReversalTask task, Discrepancy discrepancy) {
        log.info("处理金额调整, orderNo: {}, amount: {}", discrepancy.getOrderNo(), task.getAmount());

        LambdaQueryWrapper<Transaction> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Transaction::getOrderNo, discrepancy.getOrderNo());
        Transaction transaction = transactionMapper.selectOne(wrapper);

        if (transaction != null) {
            transaction.setAmount(discrepancy.getChannelAmount());
            transaction.setUpdateTime(LocalDateTime.now());
            transactionMapper.updateById(transaction);
            task.setErrorMsg("金额调整完成");
        } else {
            task.setErrorMsg("金额调整警告：未找到对应的交易记录");
        }
    }

    private void handleTaskFailure(ReversalTask task, Exception e) {
        task.setRetryCount(task.getRetryCount() + 1);
        task.setErrorMsg(e.getMessage());

        if (task.getRetryCount() >= task.getMaxRetry()) {
            task.setStatus(3);
            log.error("冲正任务已达最大重试次数，标记为失败, taskId: {}", task.getId());
        } else {
            task.setStatus(0);
            task.setUpdateTime(LocalDateTime.now());
        }

        reversalTaskMapper.updateById(task);
    }

    @Override
    public ReversalTask getReversalTaskById(Long id) {
        return reversalTaskMapper.selectById(id);
    }

    @Override
    public List<ReversalTask> listReversalTasks(String channelCode, Integer status) {
        LambdaQueryWrapper<ReversalTask> wrapper = new LambdaQueryWrapper<>();
        if (channelCode != null) {
            wrapper.eq(ReversalTask::getChannelCode, channelCode);
        }
        if (status != null) {
            wrapper.eq(ReversalTask::getStatus, status);
        }
        wrapper.orderByDesc(ReversalTask::getCreateTime);
        return reversalTaskMapper.selectList(wrapper);
    }
}
