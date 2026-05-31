package com.distributed.lock.monitor;

import com.distributed.lock.core.LockEvent;
import com.distributed.lock.core.LockEventListener;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class LockEventEsStorage implements LockEventListener {

    private final LockEventEsRepository repository;

    @Autowired
    public LockEventEsStorage(LockEventEsRepository repository) {
        this.repository = repository;
    }

    @Override
    public void onEvent(LockEvent event) {
        LockEventDocument document = convertToDocument(event);
        repository.save(document);
    }

    private LockEventDocument convertToDocument(LockEvent event) {
        LockEventDocument document = new LockEventDocument();
        BeanUtils.copyProperties(event, document);
        if (event.getEventType() != null) {
            document.setEventType(event.getEventType().name());
        }
        return document;
    }
}