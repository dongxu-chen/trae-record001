package com.medical.stockwarning.service;

import com.medical.stockwarning.dto.ReorderPointDTO;
import com.medical.stockwarning.entity.Medicine;
import com.medical.stockwarning.entity.Warehouse;
import com.medical.stockwarning.repository.ConsumptionHistoryRepository;
import com.medical.stockwarning.repository.MedicineRepository;
import com.medical.stockwarning.repository.StockRepository;
import com.medical.stockwarning.repository.WarehouseRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.math3.distribution.NormalDistribution;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class ReorderCalculationService {

    private final ConsumptionHistoryRepository consumptionHistoryRepository;
    private final StockRepository stockRepository;
    private final MedicineRepository medicineRepository;
    private final WarehouseRepository warehouseRepository;
    private final RedisCacheService redisCacheService;

    @Value("${app.stock.default-lead-time-days:14}")
    private int defaultLeadTimeDays;

    @Value("${app.stock.service-level:0.95}")
    private double serviceLevel;

    @Value("${app.stock.review-period-days:30}")
    private int reviewPeriodDays;

    @Value("${app.stock.history-days:90}")
    private int historyDays;

    public ReorderPointDTO calculateReorderPoint(Long warehouseId, Long medicineId) {
        ReorderPointDTO cached = redisCacheService.getCachedReorderPoint(warehouseId, medicineId);
        if (cached != null) {
            log.debug("Using cached reorder point for warehouse {}, medicine {}", warehouseId, medicineId);
            return cached;
        }

        Medicine medicine = medicineRepository.findById(medicineId)
                .orElseThrow(() -> new IllegalArgumentException("Medicine not found: " + medicineId));
        Warehouse warehouse = warehouseRepository.findById(warehouseId)
                .orElseThrow(() -> new IllegalArgumentException("Warehouse not found: " + warehouseId));

        BigDecimal avgDailyConsumption = calculateAverageDailyConsumption(warehouseId, medicineId);
        BigDecimal stdDevConsumption = calculateConsumptionStdDev(warehouseId, medicineId);
        int currentStock = getCurrentAvailableStock(warehouseId, medicineId);

        double zValue = calculateZValue(serviceLevel);

        int safetyStock = calculateSafetyStockWithQuantile(zValue, stdDevConsumption, defaultLeadTimeDays);
        int reorderPoint = calculateReorderPointWithQuantile(
                avgDailyConsumption, defaultLeadTimeDays, safetyStock);
        int maxStock = calculateMaxStockWithQuantile(
                avgDailyConsumption, defaultLeadTimeDays, reviewPeriodDays, safetyStock);

        ReorderPointDTO result = ReorderPointDTO.builder()
                .medicineId(medicineId)
                .warehouseId(warehouseId)
                .medicineName(medicine.getMedicineName())
                .warehouseName(warehouse.getWarehouseName())
                .avgDailyConsumption(avgDailyConsumption)
                .leadTimeDays(defaultLeadTimeDays)
                .currentStock(currentStock)
                .safetyStock(safetyStock)
                .reorderPoint(reorderPoint)
                .maxStock(maxStock)
                .serviceLevel(serviceLevel)
                .zValue(zValue)
                .stdDevConsumption(stdDevConsumption)
                .build();

        redisCacheService.cacheReorderPoint(warehouseId, medicineId, result);
        log.info("Calculated reorder point for warehouse {}, medicine {}: reorderPoint={}, safetyStock={}, currentStock={}, serviceLevel={}",
                warehouseId, medicineId, reorderPoint, safetyStock, currentStock, serviceLevel);

        return result;
    }

    public List<ReorderPointDTO> calculateReorderPointsForWarehouse(Long warehouseId) {
        List<Long> medicineIds = stockRepository.findDistinctMedicineIds(warehouseId);
        List<ReorderPointDTO> results = new ArrayList<>();

        for (Long medicineId : medicineIds) {
            try {
                ReorderPointDTO reorderPoint = calculateReorderPoint(warehouseId, medicineId);
                results.add(reorderPoint);
            } catch (Exception e) {
                log.error("Error calculating reorder point for warehouse {}, medicine {}: {}",
                        warehouseId, medicineId, e.getMessage());
            }
        }

        return results;
    }

    public List<ReorderPointDTO> calculateAllReorderPoints() {
        List<Warehouse> warehouses = warehouseRepository.findByStatus(1);
        List<ReorderPointDTO> results = new ArrayList<>();

        for (Warehouse warehouse : warehouses) {
            results.addAll(calculateReorderPointsForWarehouse(warehouse.getId()));
        }

        return results;
    }

    public List<ReorderPointDTO> getLowStockItems() {
        return calculateAllReorderPoints().stream()
                .filter(r -> r.getCurrentStock() < r.getReorderPoint())
                .toList();
    }

    public List<ReorderPointDTO> getCriticalStockItems() {
        return calculateAllReorderPoints().stream()
                .filter(r -> r.getCurrentStock() < r.getSafetyStock())
                .toList();
    }

    private BigDecimal calculateAverageDailyConsumption(Long warehouseId, Long medicineId) {
        LocalDate endDate = LocalDate.now();
        LocalDate startDate = endDate.minusDays(historyDays);

        BigDecimal avg = consumptionHistoryRepository.calculateAverageDailyConsumption(
                warehouseId, medicineId, startDate, endDate);

        if (avg == null || avg.compareTo(BigDecimal.ZERO) == 0) {
            avg = BigDecimal.ONE;
            log.debug("No consumption history for warehouse {}, medicine {}, using default value 1",
                    warehouseId, medicineId);
        }

        return avg.setScale(2, RoundingMode.HALF_UP);
    }

    private BigDecimal calculateConsumptionStdDev(Long warehouseId, Long medicineId) {
        LocalDate endDate = LocalDate.now();
        LocalDate startDate = endDate.minusDays(historyDays);

        BigDecimal stdDev = consumptionHistoryRepository.calculateConsumptionStdDev(
                warehouseId, medicineId, startDate, endDate);

        return stdDev != null ? stdDev : BigDecimal.ZERO;
    }

    private int getCurrentAvailableStock(Long warehouseId, Long medicineId) {
        Integer stock = stockRepository.sumAvailableQuantity(warehouseId, medicineId);
        return stock != null ? stock : 0;
    }

    private double calculateZValue(double serviceLevel) {
        try {
            NormalDistribution normalDist = new NormalDistribution(0, 1);
            return normalDist.inverseCumulativeProbability(serviceLevel);
        } catch (Exception e) {
            log.warn("Failed to calculate Z-value for service level {}, using default 1.645", serviceLevel);
            return 1.645;
        }
    }

    private int calculateSafetyStockWithQuantile(double zValue, BigDecimal stdDevConsumption, int leadTimeDays) {
        double stdDev = stdDevConsumption.doubleValue();
        double safetyStock = zValue * stdDev * Math.sqrt(leadTimeDays);
        return (int) Math.ceil(safetyStock);
    }

    private int calculateReorderPointWithQuantile(BigDecimal avgDailyConsumption, int leadTimeDays, int safetyStock) {
        double expectedDemandDuringLeadTime = avgDailyConsumption.doubleValue() * leadTimeDays;
        double reorderPoint = expectedDemandDuringLeadTime + safetyStock;
        return (int) Math.ceil(reorderPoint);
    }

    private int calculateMaxStockWithQuantile(BigDecimal avgDailyConsumption, int leadTimeDays,
                                                int reviewPeriodDays, int safetyStock) {
        double expectedDemandDuringCycle = avgDailyConsumption.doubleValue() * (leadTimeDays + reviewPeriodDays);
        double maxStock = expectedDemandDuringCycle + safetyStock;
        return (int) Math.ceil(maxStock);
    }

    public int calculatePurchaseQuantity(Long warehouseId, Long medicineId) {
        ReorderPointDTO reorderPoint = calculateReorderPoint(warehouseId, medicineId);
        int currentStock = reorderPoint.getCurrentStock();
        int maxStock = reorderPoint.getMaxStock();
        int purchaseQuantity = maxStock - currentStock;

        return Math.max(purchaseQuantity, 0);
    }

    public void refreshCache() {
        redisCacheService.evictAllReorderPointCache();
        log.info("Refreshed reorder point cache");
    }

    public void setServiceLevel(double serviceLevel) {
        this.serviceLevel = serviceLevel;
    }

    public double getServiceLevel() {
        return serviceLevel;
    }
}
