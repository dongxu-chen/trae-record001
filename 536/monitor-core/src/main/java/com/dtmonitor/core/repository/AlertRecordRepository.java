package com.dtmonitor.core.repository;

import com.dtmonitor.core.model.entity.AlertRecord;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface AlertRecordRepository extends JpaRepository<AlertRecord, Long> {

    Page<AlertRecord> findByAcknowledgedFalse(Pageable pageable);

    Page<AlertRecord> findByXid(String xid, Pageable pageable);

    long countByAcknowledgedFalse();
}
