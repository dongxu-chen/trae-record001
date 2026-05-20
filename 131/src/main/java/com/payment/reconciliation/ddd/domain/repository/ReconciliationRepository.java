package com.payment.reconciliation.ddd.domain.repository;

import com.payment.reconciliation.ddd.core.EventStore;
import com.payment.reconciliation.ddd.domain.aggregate.ReconciliationAggregate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

@Repository
public class ReconciliationRepository {

    @Autowired
    private EventStore eventStore;

    public void save(ReconciliationAggregate aggregate) {
        eventStore.save(
                aggregate.getId(),
                aggregate.getUncommittedEvents(),
                aggregate.getVersion()
        );
        aggregate.clearUncommittedEvents();
    }

    public ReconciliationAggregate load(String reconciliationNo) {
        ReconciliationAggregate aggregate = new ReconciliationAggregate();
        aggregate.loadFromHistory(eventStore.loadEvents(reconciliationNo));
        aggregate.setId(reconciliationNo);
        return aggregate;
    }
}
