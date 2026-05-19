package com.payment.reconciliation.ddd.application.service;

import com.payment.reconciliation.ddd.application.query.ReconciliationDoc;
import com.payment.reconciliation.ddd.core.DomainEvent;
import com.payment.reconciliation.ddd.core.EventStore;
import com.payment.reconciliation.ddd.domain.event.ReconciliationCompletedEvent;
import com.payment.reconciliation.ddd.domain.event.ReconciliationStartedEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.elasticsearch.core.ElasticsearchRestTemplate;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class EventReplayService {

    private static final Logger log = LoggerFactory.getLogger(EventReplayService.class);

    @Autowired
    private EventStore eventStore;

    @Autowired
    private ElasticsearchRestTemplate elasticsearchTemplate;

    public void replayAllEvents() {
        log.info("开始重放所有事件");

        try {
            elasticsearchTemplate.indexOps(ReconciliationDoc.class).delete();
            elasticsearchTemplate.indexOps(ReconciliationDoc.class).create();
        } catch (Exception e) {
            log.warn("删除索引失败，可能不存在", e);
        }

        List<DomainEvent> events = eventStore.replayAllEvents();
        log.info("共加载 {} 个事件", events.size());

        int count = 0;
        for (DomainEvent event : events) {
            try {
                replaySingleEvent(event);
                count++;
            } catch (Exception e) {
                log.error("重放事件失败, eventType: {}", event.getEventType(), e);
            }
        }

        log.info("事件重放完成，成功重放 {} 个事件", count);
    }

    public void replayEventsByAggregateType(String aggregateType) {
        log.info("开始重放指定类型的事件, aggregateType: {}", aggregateType);
        List<DomainEvent> events = eventStore.replayEventsByAggregateType(aggregateType);

        int count = 0;
        for (DomainEvent event : events) {
            try {
                replaySingleEvent(event);
                count++;
            } catch (Exception e) {
                log.error("重放事件失败, eventType: {}", event.getEventType(), e);
            }
        }

        log.info("事件重放完成，成功重放 {} 个事件", count);
    }

    private void replaySingleEvent(DomainEvent event) {
        if (event instanceof ReconciliationStartedEvent) {
            ReconciliationStartedEvent startedEvent = (ReconciliationStartedEvent) event;
            ReconciliationDoc doc = new ReconciliationDoc();
            doc.setReconciliationNo(startedEvent.getReconciliationNo());
            doc.setChannelCode(startedEvent.getChannelCode());
            doc.setReconciliationDate(startedEvent.getReconciliationDate().toString());
            doc.setStatus(0);
            doc.setCreateTime(startedEvent.getOccurredOn().toString());
            elasticsearchTemplate.save(doc);
        } else if (event instanceof ReconciliationCompletedEvent) {
            ReconciliationCompletedEvent completedEvent = (ReconciliationCompletedEvent) event;
            ReconciliationDoc doc = elasticsearchTemplate.get(completedEvent.getReconciliationNo(), ReconciliationDoc.class);
            if (doc != null) {
                doc.setSysTotalCount(completedEvent.getSysTotalCount());
                doc.setSysTotalAmount(completedEvent.getSysTotalAmount());
                doc.setChannelTotalCount(completedEvent.getChannelTotalCount());
                doc.setChannelTotalAmount(completedEvent.getChannelTotalAmount());
                doc.setMatchedCount(completedEvent.getMatchedCount());
                doc.setMatchedAmount(completedEvent.getMatchedAmount());
                doc.setLongCount(completedEvent.getLongCount());
                doc.setLongAmount(completedEvent.getLongAmount());
                doc.setShortCount(completedEvent.getShortCount());
                doc.setShortAmount(completedEvent.getShortAmount());
                doc.setStatus(1);
                elasticsearchTemplate.save(doc);
            }
        }
    }
}
