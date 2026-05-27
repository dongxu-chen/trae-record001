package com.medical.stockwarning.repository;

import com.medical.stockwarning.entity.PurchasePlan;
import com.medical.stockwarning.enums.ApprovalStatus;
import com.medical.stockwarning.enums.PurchaseStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface PurchasePlanRepository extends JpaRepository<PurchasePlan, Long> {

    Optional<PurchasePlan> findByPlanNo(String planNo);

    List<PurchasePlan> findByWarehouseIdAndStatus(Long warehouseId, PurchaseStatus status);

    List<PurchasePlan> findByMedicineIdAndStatus(Long medicineId, PurchaseStatus status);

    List<PurchasePlan> findByWarehouseIdAndApprovalStatus(Long warehouseId, ApprovalStatus approvalStatus);

    List<PurchasePlan> findByStatus(PurchaseStatus status);

    List<PurchasePlan> findByApprovalStatus(ApprovalStatus approvalStatus);

    @Query("SELECT pp FROM PurchasePlan pp WHERE pp.warehouseId = :warehouseId AND pp.medicineId = :medicineId AND pp.status IN :statuses")
    List<PurchasePlan> findByWarehouseAndMedicineAndStatusIn(
            @Param("warehouseId") Long warehouseId,
            @Param("medicineId") Long medicineId,
            @Param("statuses") List<PurchaseStatus> statuses);

    @Query("SELECT COUNT(pp) FROM PurchasePlan pp WHERE pp.warehouseId = :warehouseId AND pp.medicineId = :medicineId AND pp.status IN :statuses")
    Long countActivePlans(@Param("warehouseId") Long warehouseId,
                          @Param("medicineId") Long medicineId,
                          @Param("statuses") List<PurchaseStatus> statuses);

    @Query("SELECT COALESCE(SUM(pp.planQuantity), 0) FROM PurchasePlan pp " +
            "WHERE pp.warehouseId = :warehouseId AND pp.medicineId = :medicineId " +
            "AND pp.status IN :statuses")
    Integer sumActivePlanQuantity(@Param("warehouseId") Long warehouseId,
                                  @Param("medicineId") Long medicineId,
                                  @Param("statuses") List<PurchaseStatus> statuses);

    List<PurchasePlan> findByPlanDateBetween(LocalDate startDate, LocalDate endDate);
}
