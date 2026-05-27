package com.medical.stockwarning.service;

import com.medical.stockwarning.entity.Medicine;
import com.medical.stockwarning.entity.Stock;
import com.medical.stockwarning.entity.Warehouse;
import com.medical.stockwarning.enums.Severity;
import com.medical.stockwarning.enums.WarningType;
import com.medical.stockwarning.repository.MedicineRepository;
import com.medical.stockwarning.repository.StockRepository;
import com.medical.stockwarning.repository.WarehouseRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class ExpiryWarningService {

    private final StockRepository stockRepository;
    private final MedicineRepository medicineRepository;
    private final WarehouseRepository warehouseRepository;
    private final WarningService warningService;
    private final RedisCacheService redisCacheService;

    @Value("${app.stock.near-expiry-days:90}")
    private int nearExpiryDays;

    @Value("${app.stock.value-weight-threshold:100.00}")
    private BigDecimal valueWeightThreshold;

    @Value("${app.stock.high-value-extra-days:30}")
    private int highValueExtraDays;

    @Transactional
    public void checkAndMarkExpiredStocks() {
        LocalDate today = LocalDate.now();
        List<Stock> expiredStocks = stockRepository.findExpiredStocks(today);

        if (expiredStocks.isEmpty()) {
            log.info("No expired stocks found");
            return;
        }

        List<Long> expiredStockIds = expiredStocks.stream()
                .map(Stock::getId)
                .toList();

        stockRepository.markAsExpired(expiredStockIds);

        for (Stock stock : expiredStocks) {
            Medicine medicine = medicineRepository.findById(stock.getMedicineId()).orElse(null);
            Warehouse warehouse = warehouseRepository.findById(stock.getWarehouseId()).orElse(null);

            BigDecimal totalValue = stock.getUnitPrice().multiply(BigDecimal.valueOf(stock.getQuantity()));

            String message = String.format("药品 %s (批次: %s) 已过期，数量: %d，总价值: %s，仓库: %s",
                    medicine != null ? medicine.getMedicineName() : "未知",
                    stock.getBatchNo(),
                    stock.getQuantity(),
                    totalValue,
                    warehouse != null ? warehouse.getWarehouseName() : "未知");

            warningService.createWarning(
                    WarningType.EXPIRED,
                    Severity.CRITICAL,
                    stock.getWarehouseId(),
                    stock.getMedicineId(),
                    stock.getBatchNo(),
                    stock.getQuantity(),
                    0,
                    message
            );
        }

        log.info("Marked {} stocks as expired", expiredStockIds.size());
    }

    @Transactional
    public void checkAndBlockNearExpiryStocks() {
        LocalDate today = LocalDate.now();
        List<Stock> allActiveStocks = stockRepository.findNearExpiryStocks(
                today, today.plusDays(nearExpiryDays + highValueExtraDays));

        if (allActiveStocks.isEmpty()) {
            log.info("No near-expiry stocks found");
            return;
        }

        List<Long> nearExpiryStockIds = new java.util.ArrayList<>();

        for (Stock stock : allActiveStocks) {
            Medicine medicine = medicineRepository.findById(stock.getMedicineId()).orElse(null);
            Warehouse warehouse = warehouseRepository.findById(stock.getWarehouseId()).orElse(null);

            int daysToExpiry = (int) (stock.getExpiryDate().toEpochDay() - today.toEpochDay());

            boolean isHighValue = stock.getUnitPrice().compareTo(valueWeightThreshold) >= 0;
            int effectiveNearExpiryDays = isHighValue ? nearExpiryDays + highValueExtraDays : nearExpiryDays;

            if (daysToExpiry <= effectiveNearExpiryDays) {
                nearExpiryStockIds.add(stock.getId());

                String valueTag = isHighValue ? "【高价值】" : "";
                String message = String.format("%s药品 %s (批次: %s) 临近效期，剩余 %d 天，数量: %d，单价: %s，仓库: %s，已自动拦截",
                        valueTag,
                        medicine != null ? medicine.getMedicineName() : "未知",
                        stock.getBatchNo(),
                        daysToExpiry,
                        stock.getQuantity(),
                        stock.getUnitPrice(),
                        warehouse != null ? warehouse.getWarehouseName() : "未知");

                Severity severity;
                if (isHighValue && daysToExpiry <= nearExpiryDays + highValueExtraDays) {
                    severity = daysToExpiry <= 30 ? Severity.CRITICAL : Severity.WARNING;
                } else {
                    severity = daysToExpiry <= 30 ? Severity.CRITICAL : Severity.WARNING;
                }

                if (isHighValue && daysToExpiry > nearExpiryDays && daysToExpiry <= nearExpiryDays + highValueExtraDays) {
                    severity = Severity.WARNING;
                }

                warningService.createWarning(
                        WarningType.NEAR_EXPIRY,
                        severity,
                        stock.getWarehouseId(),
                        stock.getMedicineId(),
                        stock.getBatchNo(),
                        stock.getQuantity(),
                        effectiveNearExpiryDays,
                        message
                );

                log.info("{}Stock {} marked as near-expiry ({} days), high-value={}",
                        valueTag, stock.getId(), daysToExpiry, isHighValue);
            }
        }

        if (!nearExpiryStockIds.isEmpty()) {
            stockRepository.markAsBlocked(nearExpiryStockIds);
            log.info("Blocked {} near-expiry stocks (high-value threshold: {}, extra days: {})",
                    nearExpiryStockIds.size(), valueWeightThreshold, highValueExtraDays);
        }
    }

    @Transactional
    public void deactivateExpiredMedicines() {
        List<Medicine> medicines = medicineRepository.findByIsActive(1);

        for (Medicine medicine : medicines) {
            List<Stock> stocks = stockRepository.findByMedicineId(medicine.getId());

            boolean allExpired = stocks.stream()
                    .allMatch(stock -> stock.getIsExpired() == 1 || stock.getQuantity() <= 0);

            if (allExpired && !stocks.isEmpty()) {
                medicine.setIsActive(0);
                medicineRepository.save(medicine);

                log.info("Deactivated medicine {} due to all stock expired", medicine.getMedicineName());

                warningService.createWarning(
                        WarningType.EXPIRED,
                        Severity.CRITICAL,
                        null,
                        medicine.getId(),
                        null,
                        null,
                        null,
                        String.format("药品 %s 所有库存已过期，已自动停用", medicine.getMedicineName())
                );
            }
        }
    }

    @Transactional
    public void runFullExpiryCheck() {
        log.info("Starting full expiry check...");
        checkAndMarkExpiredStocks();
        checkAndBlockNearExpiryStocks();
        deactivateExpiredMedicines();
        log.info("Full expiry check completed");
    }

    public List<Stock> getExpiredStocks(Long warehouseId) {
        LocalDate today = LocalDate.now();
        return stockRepository.findExpiredStocks(today).stream()
                .filter(stock -> warehouseId == null || stock.getWarehouseId().equals(warehouseId))
                .toList();
    }

    public List<Stock> getNearExpiryStocks(Long warehouseId) {
        LocalDate today = LocalDate.now();
        LocalDate nearExpiryDate = today.plusDays(nearExpiryDays + highValueExtraDays);
        return stockRepository.findNearExpiryStocks(today, nearExpiryDate).stream()
                .filter(stock -> warehouseId == null || stock.getWarehouseId().equals(warehouseId))
                .toList();
    }

    public List<Stock> getHighValueNearExpiryStocks(Long warehouseId) {
        LocalDate today = LocalDate.now();
        LocalDate nearExpiryDate = today.plusDays(nearExpiryDays + highValueExtraDays);
        return stockRepository.findNearExpiryStocks(today, nearExpiryDate).stream()
                .filter(stock -> warehouseId == null || stock.getWarehouseId().equals(warehouseId))
                .filter(stock -> stock.getUnitPrice().compareTo(valueWeightThreshold) >= 0)
                .toList();
    }

    public int getNearExpiryDays() {
        return nearExpiryDays;
    }

    public void setNearExpiryDays(int days) {
        this.nearExpiryDays = days;
    }

    public BigDecimal getValueWeightThreshold() {
        return valueWeightThreshold;
    }

    public void setValueWeightThreshold(BigDecimal threshold) {
        this.valueWeightThreshold = threshold;
    }

    public int getHighValueExtraDays() {
        return highValueExtraDays;
    }

    public void setHighValueExtraDays(int days) {
        this.highValueExtraDays = days;
    }
}
