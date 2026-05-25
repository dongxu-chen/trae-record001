package com.property.repair.repository;

import com.property.repair.entity.OrderPart;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface OrderPartRepository extends JpaRepository<OrderPart, Long> {

    List<OrderPart> findByOrderId(Long orderId);

    List<OrderPart> findByOrderIdAndStatus(Long orderId, String status);
}
