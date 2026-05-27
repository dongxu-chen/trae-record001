package com.medical.stockwarning.repository;

import com.medical.stockwarning.entity.WarningLog;
import com.medical.stockwarning.enums.WarningType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface WarningLogRepository extends JpaRepository<WarningLog, Long> {

    List<WarningLog> findByWarningTypeAndIsResolved(WarningType warningType, Integer isResolved);

    List<WarningLog> findByMedicineIdAndWarningType(Long medicineId, WarningType warningType);

    List<WarningLog> findByWarehouseIdAndWarningType(Long warehouseId, WarningType warningType);

    @Query("SELECT w FROM WarningLog w WHERE w.warningType = :warningType AND w.isResolved = 0 AND w.createTime > :createTime")
    List<WarningLog> findUnresolvedByTypeAndTime(@Param("warningType") WarningType warningType,
                                                  @Param("createTime") LocalDateTime createTime);

    @Query("SELECT w FROM WarningLog w WHERE w.medicineId = :medicineId AND w.warehouseId = :warehouseId " +
            "AND w.warningType = :warningType AND w.isResolved = 0")
    List<WarningLog> findUnresolvedWarning(@Param("medicineId") Long medicineId,
                                            @Param("warehouseId") Long warehouseId,
                                            @Param("warningType") WarningType warningType);

    @Query("SELECT w FROM WarningLog w WHERE w.isResolved = 0")
    List<WarningLog> findAllUnresolved();

    List<WarningLog> findByWarningType(WarningType warningType);

    List<WarningLog> findByIsResolved(Integer isResolved);
}
