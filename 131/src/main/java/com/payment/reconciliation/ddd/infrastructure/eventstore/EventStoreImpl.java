package com.payment.reconciliation.ddd.infrastructure.eventstore;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.payment.reconciliation.ddd.core.DomainEvent;
import com.payment.reconciliation.ddd.core.EventStore;
import com.payment.reconciliation.ddd.domain.event.ChannelTransactionCreatedEvent;
import com.payment.reconciliation.ddd.domain.event.DiscrepancyDetectedEvent;
import com.payment.reconciliation.ddd.domain.event.ReconciliationCompletedEvent;
import com.payment.reconciliation.ddd.domain.event.ReconciliationStartedEvent;
import com.payment.reconciliation.ddd.domain.event.TransactionCreatedEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Repository
public class EventStoreImpl implements EventStore {

    private static final Logger log = LoggerFactory.getLogger(EventStoreImpl.class);

    @Autowired
    private EventStoreMapper eventStoreMapper;

    @Autowired
    private ObjectMapper objectMapper;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void save(String aggregateId, List<DomainEvent> events, Long expectedVersion) {
        log.info("保存事件到EventStore, aggregateId: {}, 事件数量: {}", aggregateId, events.size());

        String aggregateType = determineAggregateType(events);

        for (DomainEvent event : events) {
            EventStoreEntity entity = new EventStoreEntity();
            entity.setEventId(UUID.randomUUID().toString());
            entity.setAggregateId(aggregateId);
            entity.setAggregateType(aggregateType);
            entity.setVersion(event.getVersion());
            entity.setEventType(event.getEventType());
            entity.setOccurredOn(event.getOccurredOn() != null ? event.getOccurredOn() : LocalDateTime.now());
            entity.setCreateTime(LocalDateTime.now());

            try {
                String eventData = objectMapper.writeValueAsString(event);
                entity.setEventData(eventData);
            } catch (Exception e) {
                log.error("序列化事件失败, eventType: {}", event.getEventType(), e);
                throw new RuntimeException("序列化事件失败", e);
            }

            eventStoreMapper.insert(entity);
            log.debug("事件保存成功, eventType: {}, version: {}", event.getEventType(), event.getVersion());
        }
    }

    private String determineAggregateType(List<DomainEvent> events) {
        if (events.isEmpty()) {
            return "Unknown";
        }
        DomainEvent firstEvent = events.get(0);
        if (firstEvent instanceof TransactionCreatedEvent) {
            return "AccountTransaction";
        } else if (firstEvent instanceof ReconciliationStartedEvent
                || firstEvent instanceof ReconciliationCompletedEvent
                || firstEvent instanceof ChannelTransactionCreatedEvent
                || firstEvent instanceof DiscrepancyDetectedEvent) {
            return "ReconciliationAggregate";
        }
        return "Unknown";
    }

    @Override
    public List<DomainEvent> loadEvents(String aggregateId) {
        log.debug("加载事件, aggregateId: {}", aggregateId);
        List<EventStoreEntity> entities = eventStoreMapper.selectByAggregateId(aggregateId);
        return convertToDomainEvents(entities);
    }

    @Override
    public List<DomainEvent> loadEventsSince(String aggregateId, Long sinceVersion) {
        log.debug("加载事件, aggregateId: {}, sinceVersion: {}", aggregateId, sinceVersion);
        List<EventStoreEntity> entities = eventStoreMapper.selectByAggregateIdAndVersion(aggregateId, sinceVersion);
        return convertToDomainEvents(entities);
    }

    @Override
    public List<DomainEvent> loadAllEventsByType(String eventType) {
        log.debug("加载事件, eventType: {}", eventType);
        List<EventStoreEntity> entities = eventStoreMapper.selectByEventType(eventType);
        return convertToDomainEvents(entities);
    }

    @Override
    public List<DomainEvent> replayAllEvents() {
        log.info("重放所有事件");
        List<EventStoreEntity> entities = eventStoreMapper.selectAllEvents();
        return convertToDomainEvents(entities);
    }

    @Override
    public List<DomainEvent> replayEventsByAggregateType(String aggregateType) {
        log.info("重放指定聚合类型的事件, aggregateType: {}", aggregateType);
        List<EventStoreEntity> entities = eventStoreMapper.selectByAggregateType(aggregateType);
        return convertToDomainEvents(entities);
    }

    private List<DomainEvent> convertToDomainEvents(List<EventStoreEntity> entities) {
        List<DomainEvent> events = new ArrayList<>();
        for (EventStoreEntity entity : entities) {
            try {
                Class<?> eventClass = getEventClass(entity.getEventType());
                if (eventClass != null) {
                    DomainEvent event = (DomainEvent) objectMapper.readValue(entity.getEventData(), eventClass);
                    event.setEventId(entity.getEventId());
                    event.setAggregateId(entity.getAggregateId());
                    event.setVersion(entity.getVersion());
                    event.setEventType(entity.getEventType());
                    event.setOccurredOn(entity.getOccurredOn());
                    events.add(event);
                }
            } catch (Exception e) {
                log.error("反序列化事件失败, eventType: {}", entity.getEventType(), e);
            }
        }
        return events;
    }

    private Class<?> getEventClass(String eventType) {
        switch (eventType) {
            case "TransactionCreated":
                return TransactionCreatedEvent.class;
            case "ReconciliationStarted":
                return ReconciliationStartedEvent.class;
            case "ReconciliationCompleted":
                return ReconciliationCompletedEvent.class;
            case "ChannelTransactionCreated":
                return ChannelTransactionCreatedEvent.class;
            case "DiscrepancyDetected":
                return DiscrepancyDetectedEvent.class;
            default:
                log.warn("未知的事件类型: {}", eventType);
                return null;
        }
    }
}
