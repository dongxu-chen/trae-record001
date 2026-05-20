package com.payment.reconciliation.ddd.core;

import java.util.List;

public interface EventStore {
    void save(String aggregateId, List<DomainEvent> events, Long expectedVersion);

    List<DomainEvent> loadEvents(String aggregateId);

    List<DomainEvent> loadEventsSince(String aggregateId, Long sinceVersion);

    List<DomainEvent> loadAllEventsByType(String eventType);

    List<DomainEvent> replayAllEvents();

    List<DomainEvent> replayEventsByAggregateType(String aggregateType);
}
