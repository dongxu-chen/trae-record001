package com.payment.reconciliation.ddd.core;

import java.time.LocalDateTime;

public abstract class DomainEvent {
    private String eventId;
    private String aggregateId;
    private Long version;
    private LocalDateTime occurredOn;
    private String eventType;

    public DomainEvent() {
        this.occurredOn = LocalDateTime.now();
    }

    public DomainEvent(String aggregateId, Long version, String eventType) {
        this.aggregateId = aggregateId;
        this.version = version;
        this.eventType = eventType;
        this.occurredOn = LocalDateTime.now();
    }

    public String getEventId() {
        return eventId;
    }

    public void setEventId(String eventId) {
        this.eventId = eventId;
    }

    public String getAggregateId() {
        return aggregateId;
    }

    public void setAggregateId(String aggregateId) {
        this.aggregateId = aggregateId;
    }

    public Long getVersion() {
        return version;
    }

    public void setVersion(Long version) {
        this.version = version;
    }

    public LocalDateTime getOccurredOn() {
        return occurredOn;
    }

    public void setOccurredOn(LocalDateTime occurredOn) {
        this.occurredOn = occurredOn;
    }

    public String getEventType() {
        return eventType;
    }

    public void setEventType(String eventType) {
        this.eventType = eventType;
    }
}
