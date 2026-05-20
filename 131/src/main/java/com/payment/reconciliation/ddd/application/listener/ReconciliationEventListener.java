package com.payment.reconciliation.ddd.application.listener;

import com.payment.reconciliation.ddd.application.query.ReconciliationDoc;
import com.payment.reconciliation.ddd.domain.event.ReconciliationCompletedEvent;
import com.payment.reconciliation.ddd.domain.event.ReconciliationStartedEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.event.EventListener;
import org.springframework.data.elasticsearch.core.ElasticsearchRestTemplate;
import org.springframework.stereotype.Component;

@Component
public class ReconciliationEventListener {

    private static final Logger log = LoggerFactory.getLogger(ReconciliationEventListener.class);

    @Autowired
    private ElasticsearchRestTemplate elasticsearchTemplate;

    @EventListener
    public void handleReconciliationStarted(ReconciliationStartedEvent event) {
        log.info("接收到对账开始事件, reconciliationNo: {}", event.getReconciliationNo());

        ReconciliationDoc doc = new ReconciliationDoc();
        doc.setReconciliationNo(event.getReconciliationNo());
        doc.setChannelCode(event.getChannelCode());
        doc.setReconciliationDate(event.getReconciliationDate().toString());
        doc.setStatus(0);
        doc.setCreateTime(event.getOccurredOn().toString());

        elasticsearchTemplate.save(doc);
        log.info("对账数据已同步到Elasticsearch, reconciliationNo: {}", event.getReconciliationNo());
    }

    @EventListener
    public void handleReconciliationCompleted(ReconciliationCompletedEvent event) {
        log.info("接收到对账完成事件, reconciliationNo: {}", event.getReconciliationNo());

        ReconciliationDoc doc = elasticsearchTemplate.get(event.getReconciliationNo(), ReconciliationDoc.class);
        if (doc != null) {
            doc.setSysTotalCount(event.getSysTotalCount());
            doc.setSysTotalAmount(event.getSysTotalAmount());
            doc.setChannelTotalCount(event.getChannelTotalCount());
            doc.setChannelTotalAmount(event.getChannelTotalAmount());
            doc.setMatchedCount(event.getMatchedCount());
            doc.setMatchedAmount(event.getMatchedAmount());
            doc.setLongCount(event.getLongCount());
            doc.setLongAmount(event.getLongAmount());
            doc.setShortCount(event.getShortCount());
            doc.setShortAmount(event.getShortAmount());
            doc.setStatus(1);

            elasticsearchTemplate.save(doc);
            log.info("对账结果已更新到Elasticsearch, reconciliationNo: {}", event.getReconciliationNo());
        }
    }
}
