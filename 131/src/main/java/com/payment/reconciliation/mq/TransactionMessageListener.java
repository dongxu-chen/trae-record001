package com.payment.reconciliation.mq;

import com.payment.reconciliation.entity.TransactionLog;
import com.payment.reconciliation.enums.BusinessTypeEnum;
import com.payment.reconciliation.enums.TransactionStatusEnum;
import com.payment.reconciliation.mapper.TransactionLogMapper;
import com.payment.reconciliation.service.ReconciliationService;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQTransactionListener;
import org.apache.rocketmq.spring.core.RocketMQLocalTransactionListener;
import org.apache.rocketmq.spring.core.RocketMQLocalTransactionState;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.Message;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Component
@RocketMQTransactionListener
public class TransactionMessageListener implements RocketMQLocalTransactionListener {

    @Autowired
    private TransactionLogMapper transactionLogMapper;

    @Autowired
    private ReconciliationService reconciliationService;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public RocketMQLocalTransactionState executeLocalTransaction(Message msg, Object arg) {
        String transactionId = msg.getHeaders().get("TRANSACTION_ID", String.class);
        String businessType = msg.getHeaders().get("BUSINESS_TYPE", String.class);
        String businessId = msg.getHeaders().get("BUSINESS_ID", String.class);

        log.info("执行本地事务, transactionId: {}, businessType: {}, businessId: {}", transactionId, businessType, businessId);

        try {
            TransactionLog transactionLog = new TransactionLog();
            transactionLog.setTransactionId(transactionId);
            transactionLog.setBusinessType(businessType);
            transactionLog.setBusinessId(businessId);
            transactionLog.setStatus(TransactionStatusEnum.PENDING.getCode());
            transactionLog.setRetryCount(0);
            transactionLog.setCreateTime(java.time.LocalDateTime.now());
            transactionLog.setUpdateTime(java.time.LocalDateTime.now());
            transactionLogMapper.insert(transactionLog);

            if (BusinessTypeEnum.RECONCILIATION.getCode().equals(businessType)) {
                reconciliationService.processReconciliation(Long.parseLong(businessId));
            } else if (BusinessTypeEnum.FUND_TRANSFER.getCode().equals(businessType)) {
                log.info("执行资金调拨本地事务, businessId: {}", businessId);
            }

            transactionLog.setStatus(TransactionStatusEnum.COMMITTED.getCode());
            transactionLog.setUpdateTime(java.time.LocalDateTime.now());
            transactionLogMapper.updateById(transactionLog);

            log.info("本地事务执行成功, transactionId: {}", transactionId);
            return RocketMQLocalTransactionState.COMMIT;

        } catch (Exception e) {
            log.error("本地事务执行失败, transactionId: {}", transactionId, e);
            return RocketMQLocalTransactionState.ROLLBACK;
        }
    }

    @Override
    public RocketMQLocalTransactionState checkLocalTransaction(Message msg) {
        String transactionId = msg.getHeaders().get("TRANSACTION_ID", String.class);

        log.info("回查本地事务状态, transactionId: {}", transactionId);

        try {
            TransactionLog transactionLog = transactionLogMapper.selectByTransactionId(transactionId);

            if (transactionLog == null) {
                log.warn("事务日志不存在, transactionId: {}", transactionId);
                return RocketMQLocalTransactionState.UNKNOWN;
            }

            if (TransactionStatusEnum.COMMITTED.getCode().equals(transactionLog.getStatus())) {
                log.info("事务已提交, transactionId: {}", transactionId);
                return RocketMQLocalTransactionState.COMMIT;
            } else if (TransactionStatusEnum.ROLLBACK.getCode().equals(transactionLog.getStatus())) {
                log.info("事务已回滚, transactionId: {}", transactionId);
                return RocketMQLocalTransactionState.ROLLBACK;
            } else {
                log.info("事务处理中, transactionId: {}", transactionId);
                return RocketMQLocalTransactionState.UNKNOWN;
            }

        } catch (Exception e) {
            log.error("回查本地事务状态异常, transactionId: {}", transactionId, e);
            return RocketMQLocalTransactionState.UNKNOWN;
        }
    }
}
