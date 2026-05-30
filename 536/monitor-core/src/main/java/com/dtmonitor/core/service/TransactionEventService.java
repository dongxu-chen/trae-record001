package com.dtmonitor.core.service;

import com.dtmonitor.core.model.entity.TransactionEvent;
import com.dtmonitor.core.repository.TransactionEventRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class TransactionEventService {

    private final TransactionEventRepository repository;

    @Transactional
    public TransactionEvent save(TransactionEvent event) {
        return repository.save(event);
    }

    public List<TransactionEvent> findByXid(String xid) {
        return repository.findByXidOrderByEventTimeDesc(xid);
    }

    public List<TransactionEvent> findByXidAndBranchId(String xid, String branchId) {
        return repository.findByXidAndBranchIdOrderByEventTimeDesc(xid, branchId);
    }

    public Page<TransactionEvent> findByXidPaged(String xid, Pageable pageable) {
        return repository.findByXid(xid, pageable);
    }
}
