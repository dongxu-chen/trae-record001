package com.dtmonitor.core.repository;

import com.dtmonitor.core.model.entity.BranchTransaction;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface BranchTransactionRepository extends JpaRepository<BranchTransaction, Long> {

    List<BranchTransaction> findByXid(String xid);

    Page<BranchTransaction> findByXid(String xid, Pageable pageable);

    List<BranchTransaction> findByXidAndBranchId(String xid, String branchId);

    long countByXid(String xid);
}
