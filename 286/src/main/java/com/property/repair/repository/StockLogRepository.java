package com.property.repair.repository;

import com.property.repair.entity.StockLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface StockLogRepository extends JpaRepository<StockLog, Long> {

    List<StockLog> findByPartIdOrderByCreateTimeDesc(Long partId);

    List<StockLog> findByOrderId(Long orderId);
}
