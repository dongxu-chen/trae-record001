package com.medical.stockwarning.service;

import com.medical.stockwarning.dto.MedicineStockDTO;
import com.medical.stockwarning.entity.Medicine;
import com.medical.stockwarning.entity.Stock;
import com.medical.stockwarning.entity.Warehouse;
import com.medical.stockwarning.repository.MedicineRepository;
import com.medical.stockwarning.repository.StockRepository;
import com.medical.stockwarning.repository.WarehouseRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class StockService {

    private final StockRepository stockRepository;
    private final MedicineRepository medicineRepository;
    private final WarehouseRepository warehouseRepository;
    private final WarningService warningService;
    private final RedisCacheService redisCacheService;

    public List<MedicineStockDTO> getStockOverview(Long warehouseId) {
        List<MedicineStockDTO> results = new ArrayList<>();
        List<Medicine> medicines = medicineRepository.findByIsActive(1);

        for (Medicine medicine : medicines) {
            Integer totalQuantity = stockRepository.sumTotalQuantity(warehouseId, medicine.getId());
            Integer availableQuantity = stockRepository.sumAvailableQuantity(warehouseId, medicine.getId());
            LocalDate earliestExpiryDate = stockRepository.findEarliestExpiryDate(warehouseId, medicine.getId());
            Long nearExpiryCount = stockRepository.countNearExpiry(warehouseId, medicine.getId());
            Long expiredCount = stockRepository.countExpired(warehouseId, medicine.getId());

            Warehouse warehouse = warehouseRepository.findById(warehouseId).orElse(null);

            MedicineStockDTO dto = MedicineStockDTO.builder()
                    .medicineId(medicine.getId())
                    .medicineCode(medicine.getMedicineCode())
                    .medicineName(medicine.getMedicineName())
                    .specification(medicine.getSpecification())
                    .manufacturer(medicine.getManufacturer())
                    .unit(medicine.getUnit())
                    .warehouseId(warehouseId)
                    .warehouseName(warehouse != null ? warehouse.getWarehouseName() : null)
                    .totalQuantity(totalQuantity != null ? totalQuantity : 0)
                    .availableQuantity(availableQuantity != null ? availableQuantity : 0)
                    .lockedQuantity(totalQuantity != null && availableQuantity != null ?
                            totalQuantity - availableQuantity : 0)
                    .earliestExpiryDate(earliestExpiryDate)
                    .nearExpiryCount(nearExpiryCount != null ? nearExpiryCount.intValue() : 0)
                    .expiredCount(expiredCount != null ? expiredCount.intValue() : 0)
                    .hasWarning(nearExpiryCount > 0 || expiredCount > 0 ||
                            (availableQuantity != null && availableQuantity == 0))
                    .build();

            results.add(dto);
        }

        return results;
    }

    public MedicineStockDTO getMedicineStock(Long warehouseId, Long medicineId) {
        Medicine medicine = medicineRepository.findById(medicineId)
                .orElseThrow(() -> new IllegalArgumentException("Medicine not found: " + medicineId));
        Warehouse warehouse = warehouseRepository.findById(warehouseId)
                .orElseThrow(() -> new IllegalArgumentException("Warehouse not found: " + warehouseId));

        Integer totalQuantity = stockRepository.sumTotalQuantity(warehouseId, medicineId);
        Integer availableQuantity = stockRepository.sumAvailableQuantity(warehouseId, medicineId);
        LocalDate earliestExpiryDate = stockRepository.findEarliestExpiryDate(warehouseId, medicineId);
        Long nearExpiryCount = stockRepository.countNearExpiry(warehouseId, medicineId);
        Long expiredCount = stockRepository.countExpired(warehouseId, medicineId);

        return MedicineStockDTO.builder()
                .medicineId(medicine.getId())
                .medicineCode(medicine.getMedicineCode())
                .medicineName(medicine.getMedicineName())
                .specification(medicine.getSpecification())
                .manufacturer(medicine.getManufacturer())
                .unit(medicine.getUnit())
                .warehouseId(warehouseId)
                .warehouseName(warehouse.getWarehouseName())
                .totalQuantity(totalQuantity != null ? totalQuantity : 0)
                .availableQuantity(availableQuantity != null ? availableQuantity : 0)
                .lockedQuantity(totalQuantity != null && availableQuantity != null ?
                        totalQuantity - availableQuantity : 0)
                .earliestExpiryDate(earliestExpiryDate)
                .nearExpiryCount(nearExpiryCount != null ? nearExpiryCount.intValue() : 0)
                .expiredCount(expiredCount != null ? expiredCount.intValue() : 0)
                .hasWarning(nearExpiryCount > 0 || expiredCount > 0 ||
                        (availableQuantity != null && availableQuantity == 0))
                .build();
    }

    public List<Stock> getStockDetails(Long warehouseId, Long medicineId) {
        return stockRepository.findByWarehouseIdAndMedicineId(warehouseId, medicineId);
    }

    public List<Stock> getAvailableStocks(Long warehouseId, Long medicineId) {
        return stockRepository.findAvailableByWarehouseAndMedicine(warehouseId, medicineId);
    }

    @Transactional
    public Stock addStock(Stock stock) {
        stock = stockRepository.save(stock);
        redisCacheService.cacheStockInfo(stock.getWarehouseId(), stock.getMedicineId(), stock.getQuantity());
        log.info("Added stock: warehouse={}, medicine={}, quantity={}",
                stock.getWarehouseId(), stock.getMedicineId(), stock.getQuantity());
        return stock;
    }

    @Transactional
    public Stock updateStock(Long stockId, Integer quantity) {
        Stock stock = stockRepository.findById(stockId)
                .orElseThrow(() -> new IllegalArgumentException("Stock not found: " + stockId));

        stock.setQuantity(quantity);
        stock = stockRepository.save(stock);

        redisCacheService.cacheStockInfo(stock.getWarehouseId(), stock.getMedicineId(), quantity);
        log.info("Updated stock: id={}, warehouse={}, medicine={}, quantity={}",
                stockId, stock.getWarehouseId(), stock.getMedicineId(), quantity);

        return stock;
    }

    @Transactional
    public void consumeStock(Long warehouseId, Long medicineId, Integer quantity, String department) {
        List<Stock> availableStocks = stockRepository.findAvailableByWarehouseAndMedicine(warehouseId, medicineId);

        int remaining = quantity;
        for (Stock stock : availableStocks) {
            if (remaining <= 0) break;

            int available = stock.getAvailableQuantity();
            int consume = Math.min(available, remaining);

            if (consume > 0) {
                stock.setQuantity(stock.getQuantity() - consume);
                stockRepository.save(stock);
                remaining -= consume;

                log.debug("Consumed {} from stock id={}", consume, stock.getId());
            }
        }

        if (remaining > 0) {
            log.warn("Insufficient stock for consumption: warehouse={}, medicine={}, requested={}, shortfall={}",
                    warehouseId, medicineId, quantity, remaining);
        }

        redisCacheService.evictStockCache(warehouseId, medicineId);
        redisCacheService.evictReorderPointCache(warehouseId, medicineId);
    }

    public List<Stock> getStocksByWarehouse(Long warehouseId) {
        return stockRepository.findByWarehouseId(warehouseId);
    }

    public List<Stock> getStocksByMedicine(Long medicineId) {
        return stockRepository.findByMedicineId(medicineId);
    }

    public Stock getStockById(Long stockId) {
        return stockRepository.findById(stockId)
                .orElseThrow(() -> new IllegalArgumentException("Stock not found: " + stockId));
    }
}
