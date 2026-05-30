package com.dtmonitor.core.service;

import com.dtmonitor.core.model.entity.AlertRecord;
import com.dtmonitor.core.repository.AlertRecordRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

@Slf4j
@Service
@RequiredArgsConstructor
public class AlertRecordService {

    private final AlertRecordRepository repository;

    @Transactional
    public AlertRecord save(AlertRecord record) {
        return repository.save(record);
    }

    public Page<AlertRecord> findUnacknowledged(Pageable pageable) {
        return repository.findByAcknowledgedFalse(pageable);
    }

    public Page<AlertRecord> findByXid(String xid, Pageable pageable) {
        return repository.findByXid(xid, pageable);
    }

    public long countUnacknowledged() {
        return repository.countByAcknowledgedFalse();
    }

    @Transactional
    public AlertRecord acknowledge(Long id, String acknowledgedBy) {
        AlertRecord record = repository.findById(id).orElse(null);
        if (record == null) {
            log.warn("Alert record not found: {}", id);
            return null;
        }
        record.setAcknowledged(true);
        record.setAcknowledgedBy(acknowledgedBy);
        record.setAcknowledgedAt(LocalDateTime.now());
        return repository.save(record);
    }
}
