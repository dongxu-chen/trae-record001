package com.distributed.lock.monitor;

import com.distributed.lock.core.LockEvent;
import org.springframework.data.elasticsearch.repository.ElasticsearchRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface LockEventEsRepository extends ElasticsearchRepository<LockEventDocument, String> {

    List<LockEventDocument> findByLockKey(String lockKey);

    List<LockEventDocument> findByLockType(String lockType);

    List<LockEventDocument> findByEventType(LockEvent.EventType eventType);

    List<LockEventDocument> findByApplicationName(String applicationName);

    List<LockEventDocument> findByTimestampBetween(long startTime, long endTime);
}