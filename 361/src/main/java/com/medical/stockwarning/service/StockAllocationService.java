package com.medical.stockwarning.service;

import com.medical.stockwarning.dto.StockAllocationDTO;
import com.medical.stockwarning.entity.Allocation;
import com.medical.stockwarning.entity.Medicine;
import com.medical.stockwarning.entity.Warehouse;
import com.medical.stockwarning.enums.AllocationStatus;
import com.medical.stockwarning.repository.AllocationRepository;
import com.medical.stockwarning.repository.MedicineRepository;
import com.medical.stockwarning.repository.StockRepository;
import com.medical.stockwarning.repository.WarehouseRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Random;

@Slf4j
@Service
@RequiredArgsConstructor
public class StockAllocationService {

    private final AllocationRepository allocationRepository;
    private final StockRepository stockRepository;
    private final MedicineRepository medicineRepository;
    private final WarehouseRepository warehouseRepository;
    private final WarningService warningService;
    private final RedisCacheService redisCacheService;

    private static final DateTimeFormatter ALLOCATION_NO_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");

    @Transactional
    public Allocation createAllocation(StockAllocationDTO dto) {
        validateAllocation(dto);

        Allocation allocation = new Allocation();
        allocation.setAllocationNo(generateAllocationNo());
        allocation.setMedicineId(dto.getMedicineId());
        allocation.setFromWarehouseId(dto.getFromWarehouseId());
        allocation.setToWarehouseId(dto.getToWarehouseId());
        allocation.setQuantity(dto.getQuantity());
        allocation.setUnitPrice(dto.getUnitPrice());
        allocation.setTotalAmount(dto.getTotalAmount() != null ? dto.getTotalAmount() :
                dto.getUnitPrice() != null ? dto.getUnitPrice().multiply(BigDecimal.valueOf(dto.getQuantity())) : null);
        allocation.setReason(dto.getReason());
        allocation.setStatus(AllocationStatus.PENDING);
        allocation.setAllocationDate(LocalDateTime.now());

        allocation = allocationRepository.save(allocation);
        log.info("Created allocation: allocationNo={}, from={}, to={}, medicine={}, quantity={}",
                allocation.getAllocationNo(), dto.getFromWarehouseId(), dto.getToWarehouseId(),
                dto.getMedicineId(), dto.getQuantity());

        return allocation;
    }

    @Transactional
    public Allocation confirmOutbound(Long allocationId) {
        Allocation allocation = allocationRepository.findById(allocationId)
                .orElseThrow(() -> new IllegalArgumentException("Allocation not found: " + allocationId));

        if (allocation.getStatus() != AllocationStatus.PENDING) {
            throw new IllegalStateException("Only PENDING allocations can be confirmed for outbound");
        }

        Integer availableStock = stockRepository.sumAvailableQuantity(
                allocation.getFromWarehouseId(), allocation.getMedicineId());
        if (availableStock < allocation.getQuantity()) {
            throw new IllegalStateException("Insufficient stock in source warehouse");
        }

        allocation.setStatus(AllocationStatus.OUT);
        allocation = allocationRepository.save(allocation);

        redisCacheService.evictStockCache(allocation.getFromWarehouseId(), allocation.getMedicineId());
        redisCacheService.evictStockCache(allocation.getToWarehouseId(), allocation.getMedicineId());

        log.info("Confirmed outbound for allocation: allocationNo={}", allocation.getAllocationNo());
        return allocation;
    }

    @Transactional
    public Allocation confirmInbound(Long allocationId) {
        Allocation allocation = allocationRepository.findById(allocationId)
                .orElseThrow(() -> new IllegalArgumentException("Allocation not found: " + allocationId));

        if (allocation.getStatus() != AllocationStatus.OUT && allocation.getStatus() != AllocationStatus.IN_TRANSIT) {
            throw new IllegalStateException("Only OUT or IN_TRANSIT allocations can be confirmed for inbound");
        }

        allocation.setStatus(AllocationStatus.IN);
        allocation = allocationRepository.save(allocation);

        redisCacheService.evictStockCache(allocation.getFromWarehouseId(), allocation.getMedicineId());
        redisCacheService.evictStockCache(allocation.getToWarehouseId(), allocation.getMedicineId());
        redisCacheService.evictReorderPointCache(allocation.getFromWarehouseId(), allocation.getMedicineId());
        redisCacheService.evictReorderPointCache(allocation.getToWarehouseId(), allocation.getMedicineId());

        log.info("Confirmed inbound for allocation: allocationNo={}", allocation.getAllocationNo());
        return allocation;
    }

    @Transactional
    public Allocation cancelAllocation(Long allocationId, String reason) {
        Allocation allocation = allocationRepository.findById(allocationId)
                .orElseThrow(() -> new IllegalArgumentException("Allocation not found: " + allocationId));

        if (allocation.getStatus() == AllocationStatus.IN) {
            throw new IllegalStateException("Completed allocations cannot be cancelled");
        }

        allocation.setStatus(AllocationStatus.CANCELLED);
        allocation.setReason(reason);
        allocation = allocationRepository.save(allocation);

        log.info("Cancelled allocation: allocationNo={}, reason={}", allocation.getAllocationNo(), reason);
        return allocation;
    }

    @Transactional
    public List<Allocation> createAutoAllocations() {
        List<Warehouse> warehouses = warehouseRepository.findByStatus(1);
        List<Allocation> allocations = new java.util.ArrayList<>();

        for (Warehouse targetWarehouse : warehouses) {
            List<Long> medicineIds = stockRepository.findDistinctMedicineIds(targetWarehouse.getId());

            for (Long medicineId : medicineIds) {
                Integer targetStock = stockRepository.sumAvailableQuantity(targetWarehouse.getId(), medicineId);
                Integer safetyStock = calculateSafetyStock(targetWarehouse.getId(), medicineId);

                if (targetStock < safetyStock) {
                    Allocation allocation = findAndCreateAllocation(medicineId, targetWarehouse.getId(), targetStock, safetyStock);
                    if (allocation != null) {
                        allocations.add(allocation);
                    }
                }
            }
        }

        return allocations;
    }

    private Allocation findAndCreateAllocation(Long medicineId, Long targetWarehouseId, Integer currentStock, Integer safetyStock) {
        List<Warehouse> warehouses = warehouseRepository.findByStatus(1);

        for (Warehouse sourceWarehouse : warehouses) {
            if (sourceWarehouse.getId().equals(targetWarehouseId)) {
                continue;
            }

            Integer sourceStock = stockRepository.sumAvailableQuantity(sourceWarehouse.getId(), medicineId);
            Integer sourceSafetyStock = calculateSafetyStock(sourceWarehouse.getId(), medicineId);

            int availableForAllocation = sourceStock - sourceSafetyStock;
            if (availableForAllocation > 0) {
                int needed = safetyStock - currentStock;
                int quantity = Math.min(availableForAllocation, needed);

                if (quantity > 0) {
                    Medicine medicine = medicineRepository.findById(medicineId).orElse(null);

                    StockAllocationDTO dto = StockAllocationDTO.builder()
                            .medicineId(medicineId)
                            .medicineName(medicine != null ? medicine.getMedicineName() : null)
                            .fromWarehouseId(sourceWarehouse.getId())
                            .fromWarehouseName(sourceWarehouse.getWarehouseName())
                            .toWarehouseId(targetWarehouseId)
                            .toWarehouseName(warehouseRepository.findById(targetWarehouseId).orElse(null).getWarehouseName())
                            .quantity(quantity)
                            .reason("Auto-allocation: low stock in target warehouse")
                            .build();

                    return createAllocation(dto);
                }
            }
        }

        return null;
    }

    private Integer calculateSafetyStock(Long warehouseId, Long medicineId) {
        Integer totalStock = stockRepository.sumTotalQuantity(warehouseId, medicineId);
        return totalStock != null ? (int) (totalStock * 0.2) : 0;
    }

    public List<Allocation> getPendingAllocations() {
        return allocationRepository.findByMedicineIdAndStatusIn(null, List.of(AllocationStatus.PENDING));
    }

    public List<Allocation> getAllocationsByMedicine(Long medicineId) {
        return allocationRepository.findByMedicineIdAndStatusIn(medicineId,
                List.of(AllocationStatus.PENDING, AllocationStatus.OUT, AllocationStatus.IN_TRANSIT));
    }

    public List<Allocation> getOutboundAllocations(Long warehouseId) {
        return allocationRepository.findOutboundByWarehouse(warehouseId,
                List.of(AllocationStatus.PENDING, AllocationStatus.OUT, AllocationStatus.IN_TRANSIT));
    }

    public List<Allocation> getInboundAllocations(Long warehouseId) {
        return allocationRepository.findInboundByWarehouse(warehouseId,
                List.of(AllocationStatus.PENDING, AllocationStatus.OUT, AllocationStatus.IN_TRANSIT));
    }

    public Allocation getAllocationById(Long allocationId) {
        return allocationRepository.findById(allocationId)
                .orElseThrow(() -> new IllegalArgumentException("Allocation not found: " + allocationId));
    }

    private void validateAllocation(StockAllocationDTO dto) {
        if (dto.getFromWarehouseId().equals(dto.getToWarehouseId())) {
            throw new IllegalArgumentException("Source and target warehouses cannot be the same");
        }

        Integer availableStock = stockRepository.sumAvailableQuantity(dto.getFromWarehouseId(), dto.getMedicineId());
        if (availableStock < dto.getQuantity()) {
            throw new IllegalArgumentException("Insufficient stock in source warehouse");
        }
    }

    private String generateAllocationNo() {
        String timestamp = LocalDateTime.now().format(ALLOCATION_NO_FORMATTER);
        int random = new Random().nextInt(1000);
        return "AL" + timestamp + String.format("%03d", random);
    }
}
