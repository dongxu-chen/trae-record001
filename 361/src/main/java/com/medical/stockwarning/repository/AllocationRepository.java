package com.medical.stockwarning.repository;

import com.medical.stockwarning.entity.Allocation;
import com.medical.stockwarning.enums.AllocationStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface AllocationRepository extends JpaRepository<Allocation, Long> {

    Optional<Allocation> findByAllocationNo(String allocationNo);

    List<Allocation> findByMedicineIdAndStatus(Long medicineId, AllocationStatus status);

    List<Allocation> findByFromWarehouseIdAndStatus(Long fromWarehouseId, AllocationStatus status);

    List<Allocation> findByToWarehouseIdAndStatus(Long toWarehouseId, AllocationStatus status);

    @Query("SELECT a FROM Allocation a WHERE a.medicineId = :medicineId AND a.status IN :statuses")
    List<Allocation> findByMedicineIdAndStatusIn(@Param("medicineId") Long medicineId,
                                                  @Param("statuses") List<AllocationStatus> statuses);

    @Query("SELECT a FROM Allocation a WHERE a.fromWarehouseId = :warehouseId AND a.status IN :statuses")
    List<Allocation> findOutboundByWarehouse(@Param("warehouseId") Long warehouseId,
                                             @Param("statuses") List<AllocationStatus> statuses);

    @Query("SELECT a FROM Allocation a WHERE a.toWarehouseId = :warehouseId AND a.status IN :statuses")
    List<Allocation> findInboundByWarehouse(@Param("warehouseId") Long warehouseId,
                                            @Param("statuses") List<AllocationStatus> statuses);

    @Query("SELECT COALESCE(SUM(a.quantity), 0) FROM Allocation a " +
            "WHERE a.medicineId = :medicineId AND a.fromWarehouseId = :warehouseId " +
            "AND a.status IN :statuses")
    Integer sumOutboundQuantity(@Param("medicineId") Long medicineId,
                                @Param("warehouseId") Long warehouseId,
                                @Param("statuses") List<AllocationStatus> statuses);

    @Query("SELECT COALESCE(SUM(a.quantity), 0) FROM Allocation a " +
            "WHERE a.medicineId = :medicineId AND a.toWarehouseId = :warehouseId " +
            "AND a.status IN :statuses")
    Integer sumInboundQuantity(@Param("medicineId") Long medicineId,
                               @Param("warehouseId") Long warehouseId,
                               @Param("statuses") List<AllocationStatus> statuses);
}
