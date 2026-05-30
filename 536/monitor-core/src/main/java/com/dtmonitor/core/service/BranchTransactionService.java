package com.dtmonitor.core.service;

import com.dtmonitor.core.model.entity.BranchTransaction;
import com.dtmonitor.core.repository.BranchTransactionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class BranchTransactionService {

    private final BranchTransactionRepository repository;

    @Transactional
    public BranchTransaction save(BranchTransaction branch) {
        return repository.save(branch);
    }

    public List<BranchTransaction> findByXid(String xid) {
        return repository.findByXid(xid);
    }

    public List<BranchTransaction> findByXidAndBranchId(String xid, String branchId) {
        return repository.findByXidAndBranchId(xid, branchId);
    }

    public long countByXid(String xid) {
        return repository.countByXid(xid);
    }
}
