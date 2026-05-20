package com.payment.reconciliation.ddd.core;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public abstract class AggregateRoot<ID> {
    private ID id;
    private Long version;
    private final List<DomainEvent> uncommittedEvents = new ArrayList<>();

    public ID getId() {
        return id;
    }

    public void setId(ID id) {
        this.id = id;
    }

    public Long getVersion() {
        return version;
    }

    public void setVersion(Long version) {
        this.version = version;
    }

    protected void apply(DomainEvent event) {
        handle(event);
        uncommittedEvents.add(event);
        if (version == null) {
            version = 1L;
        } else {
            version++;
        }
    }

    protected abstract void handle(DomainEvent event);

    public List<DomainEvent> getUncommittedEvents() {
        return Collections.unmodifiableList(uncommittedEvents);
    }

    public void clearUncommittedEvents() {
        uncommittedEvents.clear();
    }

    public void loadFromHistory(List<DomainEvent> events) {
        for (DomainEvent event : events) {
            handle(event);
            this.version = event.getVersion();
        }
    }
}
