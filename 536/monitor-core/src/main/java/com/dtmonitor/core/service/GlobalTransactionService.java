package com.dtmonitor.core.service;

import com.dtmonitor.core.enums.TransactionMode;
import com.dtmonitor.core.enums.TransactionStatus;
import com.dtmonitor.core.model.entity.GlobalTransaction;
import com.dtmonitor.core.repository.GlobalTransactionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class GlobalTransactionService {

    private final GlobalTransactionRepository repository;

    @Transactional
    public GlobalTransaction save(GlobalTransaction transaction) {
        return repository.save(transaction);
    }

    public GlobalTransaction findById(String xid) {
        return repository.findById(xid).orElse(null);
    }

    public Page<GlobalTransaction> search(TransactionMode mode, TransactionStatus status,
                                          String applicationId, String trafficColor,
                                          String businessType, LocalDateTime startTime,
                                          LocalDateTime endTime, Pageable pageable) {
        return repository.search(mode, status, applicationId, trafficColor, businessType, startTime, endTime, pageable);
    }

    public Page<GlobalTransaction> findByTrafficColor(String trafficColor, Pageable pageable) {
        return repository.findByTrafficColor(trafficColor, pageable);
    }

    public Page<GlobalTransaction> findByBusinessType(String businessType, Pageable pageable) {
        return repository.findByBusinessType(businessType, pageable);
    }

    public List<String> findDistinctTrafficColors() {
        return repository.findDistinctTrafficColors();
    }

    public List<String> findDistinctBusinessTypes() {
        return repository.findDistinctBusinessTypes();
    }

    @Transactional
    public GlobalTransaction updateTrafficInfo(String xid, String trafficColor,
                                               String businessType, Map<String, String> tags) {
        GlobalTransaction tx = findById(xid);
        if (tx == null) {
            log.warn("Transaction not found: {}", xid);
            return null;
        }
        if (trafficColor != null) tx.setTrafficColor(trafficColor);
        if (businessType != null) tx.setBusinessType(businessType);
        if (tags != null) tx.getTags().putAll(tags);
        return repository.save(tx);
    }

    public Page<GlobalTransaction> findByStatus(TransactionStatus status, Pageable pageable) {
        return repository.findByStatus(status, pageable);
    }

    public Page<GlobalTransaction> findByMode(TransactionMode mode, Pageable pageable) {
        return repository.findByMode(mode, pageable);
    }

    @Transactional
    public GlobalTransaction updateStatus(String xid, TransactionStatus status) {
        GlobalTransaction tx = findById(xid);
        if (tx == null) {
            log.warn("Transaction not found: {}", xid);
            return null;
        }
        tx.setStatus(status);
        if (status == TransactionStatus.COMMITTED || status == TransactionStatus.ROLLEDBACK
                || status == TransactionStatus.FAILED) {
            tx.setEndTime(LocalDateTime.now());
        }
        return repository.save(tx);
    }

    public Map<TransactionStatus, Long> countByStatus() {
        List<Object[]> results = repository.countByStatusGroup();
        return results.stream().collect(Collectors.toMap(
                r -> (TransactionStatus) r[0],
                r -> (Long) r[1]
        ));
    }

    public Map<TransactionMode, Long> countByMode() {
        List<Object[]> results = repository.countByModeGroup();
        return results.stream().collect(Collectors.toMap(
                r -> (TransactionMode) r[0],
                r -> (Long) r[1]
        ));
    }

    public List<GlobalTransaction> findTimeoutCandidates(LocalDateTime threshold) {
        return repository.findByStatusAndBeginTimeBefore(TransactionStatus.BEGIN, threshold);
    }

    public long countActive() {
        return repository.countByStatus(TransactionStatus.BEGIN)
                + repository.countByStatus(TransactionStatus.COMMITTING)
                + repository.countByStatus(TransactionStatus.ROLLBACKING);
    }

    public long countTotalSince(LocalDateTime since) {
        return repository.countSince(since);
    }
}
