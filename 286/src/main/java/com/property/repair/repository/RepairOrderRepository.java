package com.property.repair.repository;

import com.property.repair.entity.RepairOrder;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface RepairOrderRepository extends JpaRepository<RepairOrder, Long> {

    RepairOrder findByOrderNo(String orderNo);

    List<RepairOrder> findByOwnerIdOrderByCreateTimeDesc(Long ownerId);

    List<RepairOrder> findByWorkerIdOrderByCreateTimeDesc(Long workerId);

    List<RepairOrder> findByStatus(String status);

    @Query("SELECT o FROM RepairOrder o WHERE o.status = :status AND o.assignTime < :time")
    List<RepairOrder> findOverdueOrders(String status, LocalDateTime time);

    @Query("SELECT COUNT(o) FROM RepairOrder o WHERE o.status = :status")
    Long countByStatus(String status);

    @Query("SELECT o.repairTypeName, COUNT(o) FROM RepairOrder o GROUP BY o.repairTypeName")
    List<Object[]> countByRepairType();

    @Query("SELECT FUNCTION('DATE', o.createTime) as date, COUNT(o) FROM RepairOrder o " +
           "WHERE o.createTime >= :startTime GROUP BY FUNCTION('DATE', o.createTime)")
    List<Object[]> countByDate(LocalDateTime startTime);

    @Query("SELECT o.workerId, o.workerName, COUNT(o), AVG(e.rating) " +
           "FROM RepairOrder o LEFT JOIN RepairEvaluation e ON o.id = e.orderId " +
           "WHERE o.workerId IS NOT NULL " +
           "GROUP BY o.workerId, o.workerName")
    List<Object[]> getWorkerStats();
}
