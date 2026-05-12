package com.ecommerce.productcenter.repository;

import com.ecommerce.productcenter.entity.StockLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface StockLogRepository extends JpaRepository<StockLog, Long> {

    List<StockLog> findBySkuIdOrderByCreatedAtDesc(Long skuId);

    Page<StockLog> findBySkuId(Long skuId, Pageable pageable);

    List<StockLog> findByOrderNo(String orderNo);

    Optional<StockLog> findFirstBySkuIdAndOrderNoAndType(Long skuId, String orderNo, StockLog.StockType type);

    Page<StockLog> findByType(StockLog.StockType type, Pageable pageable);
}
