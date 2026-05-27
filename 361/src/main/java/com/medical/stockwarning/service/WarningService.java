package com.medical.stockwarning.service;

import com.medical.stockwarning.dto.WarningDTO;
import com.medical.stockwarning.entity.Medicine;
import com.medical.stockwarning.entity.Warehouse;
import com.medical.stockwarning.entity.WarningLog;
import com.medical.stockwarning.enums.Severity;
import com.medical.stockwarning.enums.WarningType;
import com.medical.stockwarning.repository.MedicineRepository;
import com.medical.stockwarning.repository.WarehouseRepository;
import com.medical.stockwarning.repository.WarningLogRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class WarningService {

    private final WarningLogRepository warningLogRepository;
    private final MedicineRepository medicineRepository;
    private final WarehouseRepository warehouseRepository;
    private final RedisCacheService redisCacheService;

    @Transactional
    public WarningLog createWarning(WarningType type, Severity severity,
                                     Long warehouseId, Long medicineId,
                                     String batchNo, Integer currentValue,
                                     Integer thresholdValue, String message) {
        List<WarningLog> existing = warningLogRepository.findUnresolvedWarning(
                medicineId, warehouseId, type);

        if (!existing.isEmpty()) {
            log.debug("Warning already exists for medicine={}, warehouse={}, type={}",
                    medicineId, warehouseId, type);
            return existing.get(0);
        }

        WarningLog warningLog = new WarningLog();
        warningLog.setWarningType(type);
        warningLog.setSeverity(severity);
        warningLog.setWarehouseId(warehouseId);
        warningLog.setMedicineId(medicineId);
        warningLog.setBatchNo(batchNo);
        warningLog.setCurrentValue(currentValue);
        warningLog.setThresholdValue(thresholdValue);
        warningLog.setMessage(message);
        warningLog.setIsResolved(0);

        warningLog = warningLogRepository.save(warningLog);

        log.info("Created warning: type={}, severity={}, medicine={}, warehouse={}, message={}",
                type, severity, medicineId, warehouseId, message);

        return warningLog;
    }

    @Transactional
    public WarningLog resolveWarning(Long warningId, String resolveBy, String resolveNote) {
        WarningLog warningLog = warningLogRepository.findById(warningId)
                .orElseThrow(() -> new IllegalArgumentException("Warning not found: " + warningId));

        warningLog.setIsResolved(1);
        warningLog.setResolveTime(LocalDateTime.now());
        warningLog.setResolveBy(resolveBy);
        warningLog.setResolveNote(resolveNote);

        warningLog = warningLogRepository.save(warningLog);

        log.info("Resolved warning: id={}, resolveBy={}", warningId, resolveBy);

        return warningLog;
    }

    public List<WarningDTO> getAllWarnings() {
        return warningLogRepository.findAll().stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
    }

    public List<WarningDTO> getUnresolvedWarnings() {
        return warningLogRepository.findAllUnresolved().stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
    }

    public List<WarningDTO> getWarningsByType(WarningType type) {
        return warningLogRepository.findByWarningTypeAndIsResolved(type, 0).stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
    }

    public List<WarningDTO> getLowStockWarnings() {
        return getWarningsByType(WarningType.LOW_STOCK);
    }

    public List<WarningDTO> getNearExpiryWarnings() {
        return getWarningsByType(WarningType.NEAR_EXPIRY);
    }

    public List<WarningDTO> getExpiredWarnings() {
        return getWarningsByType(WarningType.EXPIRED);
    }

    public WarningLog getWarningById(Long warningId) {
        return warningLogRepository.findById(warningId)
                .orElseThrow(() -> new IllegalArgumentException("Warning not found: " + warningId));
    }

    public long countUnresolvedWarnings() {
        return warningLogRepository.findAllUnresolved().size();
    }

    public long countWarningsByType(WarningType type) {
        return warningLogRepository.findByWarningTypeAndIsResolved(type, 0).size();
    }

    public void checkAndCreateLowStockWarnings(Long warehouseId, Long medicineId,
                                                int currentStock, int reorderPoint,
                                                String medicineName, String warehouseName) {
        if (currentStock < reorderPoint) {
            Severity severity = currentStock < (reorderPoint / 2) ? Severity.CRITICAL : Severity.WARNING;

            String message = String.format("药品 %s 在仓库 %s 库存不足，当前库存: %d，补货点: %d",
                    medicineName, warehouseName, currentStock, reorderPoint);

            createWarning(WarningType.LOW_STOCK, severity, warehouseId, medicineId,
                    null, currentStock, reorderPoint, message);
        }
    }

    private WarningDTO toDTO(WarningLog warningLog) {
        Medicine medicine = null;
        Warehouse warehouse = null;

        if (warningLog.getMedicineId() != null) {
            medicine = medicineRepository.findById(warningLog.getMedicineId()).orElse(null);
        }
        if (warningLog.getWarehouseId() != null) {
            warehouse = warehouseRepository.findById(warningLog.getWarehouseId()).orElse(null);
        }

        return WarningDTO.builder()
                .id(warningLog.getId())
                .warningType(warningLog.getWarningType())
                .severity(warningLog.getSeverity())
                .warehouseId(warningLog.getWarehouseId())
                .warehouseName(warehouse != null ? warehouse.getWarehouseName() : null)
                .medicineId(warningLog.getMedicineId())
                .medicineName(medicine != null ? medicine.getMedicineName() : null)
                .batchNo(warningLog.getBatchNo())
                .currentValue(warningLog.getCurrentValue())
                .thresholdValue(warningLog.getThresholdValue())
                .message(warningLog.getMessage())
                .resolved(warningLog.getIsResolved() == 1)
                .createTime(warningLog.getCreateTime())
                .build();
    }

    @Transactional
    public void batchResolveWarnings(List<Long> warningIds, String resolveBy, String resolveNote) {
        for (Long warningId : warningIds) {
            try {
                resolveWarning(warningId, resolveBy, resolveNote);
            } catch (Exception e) {
                log.error("Error resolving warning {}: {}", warningId, e.getMessage());
            }
        }
    }
}
