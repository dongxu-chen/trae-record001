package com.medical.stockwarning.repository;

import com.medical.stockwarning.entity.Stock;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface StockRepository extends JpaRepository<Stock, Long> {

    List<Stock> findByWarehouseIdAndMedicineId(Long warehouseId, Long medicineId);

    List<Stock> findByMedicineId(Long medicineId);

    List<Stock> findByWarehouseId(Long warehouseId);

    @Query("SELECT s FROM Stock s WHERE s.warehouseId = :warehouseId AND s.medicineId = :medicineId AND s.isExpired = 0 AND s.isBlocked = 0")
    List<Stock> findAvailableByWarehouseAndMedicine(@Param("warehouseId") Long warehouseId, @Param("medicineId") Long medicineId);

    @Query("SELECT COALESCE(SUM(s.quantity - s.lockedQuantity), 0) FROM Stock s WHERE s.warehouseId = :warehouseId AND s.medicineId = :medicineId AND s.isExpired = 0 AND s.isBlocked = 0")
    Integer sumAvailableQuantity(@Param("warehouseId") Long warehouseId, @Param("medicineId") Long medicineId);

    @Query("SELECT COALESCE(SUM(s.quantity), 0) FROM Stock s WHERE s.warehouseId = :warehouseId AND s.medicineId = :medicineId")
    Integer sumTotalQuantity(@Param("warehouseId") Long warehouseId, @Param("medicineId") Long medicineId);

    @Query("SELECT MIN(s.expiryDate) FROM Stock s WHERE s.warehouseId = :warehouseId AND s.medicineId = :medicineId AND s.isExpired = 0")
    LocalDate findEarliestExpiryDate(@Param("warehouseId") Long warehouseId, @Param("medicineId") Long medicineId);

    @Query("SELECT COUNT(s) FROM Stock s WHERE s.warehouseId = :warehouseId AND s.medicineId = :medicineId AND s.isBlocked = 1")
    Long countNearExpiry(@Param("warehouseId") Long warehouseId, @Param("medicineId") Long medicineId);

    @Query("SELECT COUNT(s) FROM Stock s WHERE s.warehouseId = :warehouseId AND s.medicineId = :medicineId AND s.isExpired = 1")
    Long countExpired(@Param("warehouseId") Long warehouseId, @Param("medicineId") Long medicineId);

    @Query("SELECT s FROM Stock s WHERE s.expiryDate <= :expiryDate AND s.isExpired = 0")
    List<Stock> findExpiredStocks(@Param("expiryDate") LocalDate expiryDate);

    @Query("SELECT s FROM Stock s WHERE s.expiryDate BETWEEN :startDate AND :endDate AND s.isExpired = 0 AND s.isBlocked = 0")
    List<Stock> findNearExpiryStocks(@Param("startDate") LocalDate startDate, @Param("endDate") LocalDate endDate);

    @Query("SELECT DISTINCT s.medicineId FROM Stock s WHERE s.warehouseId = :warehouseId")
    List<Long> findDistinctMedicineIds(@Param("warehouseId") Long warehouseId);

    @Modifying
    @Query("UPDATE Stock s SET s.isExpired = 1 WHERE s.id IN :ids")
    int markAsExpired(@Param("ids") List<Long> ids);

    @Modifying
    @Query("UPDATE Stock s SET s.isBlocked = 1 WHERE s.id IN :ids")
    int markAsBlocked(@Param("ids") List<Long> ids);
}
