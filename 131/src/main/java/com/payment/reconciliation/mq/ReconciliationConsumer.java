package com.payment.reconciliation.mq;

import com.payment.reconciliation.service.ReconciliationService;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RocketMQMessageListener(
        topic = "${reconciliation.mq.topic.reconciliation}",
        consumerGroup = "reconciliation-consumer-group"
)
public class ReconciliationConsumer implements RocketMQListener<Long> {

    @Autowired
    private ReconciliationService reconciliationService;

    @Override
    public void onMessage(Long reconciliationId) {
        log.info("收到对账消息, reconciliationId: {}", reconciliationId);
        try {
            reconciliationService.processReconciliation(reconciliationId);
            log.info("对账消息处理完成, reconciliationId: {}", reconciliationId);
        } catch (Exception e) {
            log.error("对账消息处理失败, reconciliationId: {}", reconciliationId, e);
            throw new RuntimeException(e);
        }
    }
}
