package com.dtmonitor.core.repository;

import com.dtmonitor.core.model.entity.TransactionEvent;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface TransactionEventRepository extends JpaRepository<TransactionEvent, Long> {

    List<TransactionEvent> findByXidOrderByEventTimeDesc(String xid);

    Page<TransactionEvent> findByXid(String xid, Pageable pageable);

    List<TransactionEvent> findByXidAndBranchIdOrderByEventTimeDesc(String xid, String branchId);
}
