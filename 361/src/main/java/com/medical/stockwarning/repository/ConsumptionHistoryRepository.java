package com.medical.stockwarning.repository;

import com.medical.stockwarning.entity.ConsumptionHistory;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

@Repository
public interface ConsumptionHistoryRepository extends JpaRepository<ConsumptionHistory, Long> {

    List<ConsumptionHistory> findByMedicineIdAndConsumptionDateBetween(
            Long medicineId, LocalDate startDate, LocalDate endDate);

    List<ConsumptionHistory> findByWarehouseIdAndMedicineIdAndConsumptionDateBetween(
            Long warehouseId, Long medicineId, LocalDate startDate, LocalDate endDate);

    @Query("SELECT COALESCE(AVG(ch.quantity), 0) FROM ConsumptionHistory ch " +
            "WHERE ch.warehouseId = :warehouseId AND ch.medicineId = :medicineId " +
            "AND ch.consumptionDate BETWEEN :startDate AND :endDate")
    BigDecimal calculateAverageDailyConsumption(
            @Param("warehouseId") Long warehouseId,
            @Param("medicineId") Long medicineId,
            @Param("startDate") LocalDate startDate,
            @Param("endDate") LocalDate endDate);

    @Query("SELECT COALESCE(SUM(ch.quantity), 0) FROM ConsumptionHistory ch " +
            "WHERE ch.warehouseId = :warehouseId AND ch.medicineId = :medicineId " +
            "AND ch.consumptionDate BETWEEN :startDate AND :endDate")
    Integer calculateTotalConsumption(
            @Param("warehouseId") Long warehouseId,
            @Param("medicineId") Long medicineId,
            @Param("startDate") LocalDate startDate,
            @Param("endDate") LocalDate endDate);

    @Query("SELECT ch.medicineId, COALESCE(AVG(ch.quantity), 0) FROM ConsumptionHistory ch " +
            "WHERE ch.warehouseId = :warehouseId " +
            "AND ch.consumptionDate BETWEEN :startDate AND :endDate " +
            "GROUP BY ch.medicineId")
    List<Object[]> calculateAvgConsumptionForAllMedicines(
            @Param("warehouseId") Long warehouseId,
            @Param("startDate") LocalDate startDate,
            @Param("endDate") LocalDate endDate);

    @Query("SELECT COALESCE(STD(ch.quantity), 0) FROM ConsumptionHistory ch " +
            "WHERE ch.warehouseId = :warehouseId AND ch.medicineId = :medicineId " +
            "AND ch.consumptionDate BETWEEN :startDate AND :endDate")
    BigDecimal calculateConsumptionStdDev(
            @Param("warehouseId") Long warehouseId,
            @Param("medicineId") Long medicineId,
            @Param("startDate") LocalDate startDate,
            @Param("endDate") LocalDate endDate);
}
