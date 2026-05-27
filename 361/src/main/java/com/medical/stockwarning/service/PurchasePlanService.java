package com.medical.stockwarning.service;

import com.medical.stockwarning.dto.PurchasePlanDTO;
import com.medical.stockwarning.dto.ReorderPointDTO;
import com.medical.stockwarning.entity.Medicine;
import com.medical.stockwarning.entity.PurchasePlan;
import com.medical.stockwarning.entity.Warehouse;
import com.medical.stockwarning.enums.ApprovalStatus;
import com.medical.stockwarning.enums.PurchaseStatus;
import com.medical.stockwarning.repository.MedicineRepository;
import com.medical.stockwarning.repository.PurchasePlanRepository;
import com.medical.stockwarning.repository.WarehouseRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Random;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
@Service
@RequiredArgsConstructor
public class PurchasePlanService {

    private final PurchasePlanRepository purchasePlanRepository;
    private final ReorderCalculationService reorderCalculationService;
    private final MedicineRepository medicineRepository;
    private final WarehouseRepository warehouseRepository;
    private final WarningService warningService;
    private final RedisCacheService redisCacheService;

    private static final DateTimeFormatter PLAN_NO_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");

    @Transactional
    public PurchasePlan generatePurchasePlan(PurchasePlanDTO planDTO) {
        PurchasePlan plan = new PurchasePlan();
        plan.setPlanNo(generatePlanNo());
        plan.setMedicineId(planDTO.getMedicineId());
        plan.setWarehouseId(planDTO.getWarehouseId());
        plan.setPlanQuantity(planDTO.getPlanQuantity());
        plan.setUnitPrice(planDTO.getUnitPrice());
        plan.setTotalAmount(planDTO.getTotalAmount() != null ? planDTO.getTotalAmount() :
                planDTO.getUnitPrice() != null ? planDTO.getUnitPrice().multiply(BigDecimal.valueOf(planDTO.getPlanQuantity())) : null);
        plan.setExpectedDate(planDTO.getExpectedDate());
        plan.setReorderPoint(planDTO.getReorderPoint());
        plan.setSafetyStock(planDTO.getSafetyStock());
        plan.setAvgConsumption(planDTO.getAvgConsumption());
        plan.setLeadTimeDays(planDTO.getLeadTimeDays());
        plan.setPlanDate(LocalDate.now());
        plan.setRemark(planDTO.getRemark());
        plan.setStatus(PurchaseStatus.PENDING);
        plan.setApprovalStatus(ApprovalStatus.PENDING);

        plan = purchasePlanRepository.save(plan);
        log.info("Generated purchase plan: planNo={}, medicineId={}, warehouseId={}, quantity={}",
                plan.getPlanNo(), plan.getMedicineId(), plan.getWarehouseId(), plan.getPlanQuantity());

        return plan;
    }

    @Transactional
    public List<PurchasePlan> generatePurchasePlansForLowStock() {
        List<ReorderPointDTO> lowStockItems = reorderCalculationService.getLowStockItems();
        log.info("Found {} low stock items for purchase planning", lowStockItems.size());

        AtomicInteger generated = new AtomicInteger(0);
        return lowStockItems.stream()
                .filter(item -> !hasActivePurchasePlan(item.getWarehouseId(), item.getMedicineId()))
                .map(item -> {
                    PurchasePlanDTO planDTO = buildPurchasePlanDTO(item);
                    PurchasePlan plan = generatePurchasePlan(planDTO);
                    generated.incrementAndGet();
                    return plan;
                })
                .toList();
    }

    @Transactional
    public PurchasePlan approvePlan(Long planId, String approver) {
        PurchasePlan plan = purchasePlanRepository.findById(planId)
                .orElseThrow(() -> new IllegalArgumentException("Purchase plan not found: " + planId));

        plan.setApprovalStatus(ApprovalStatus.APPROVED);
        plan.setStatus(PurchaseStatus.APPROVED);
        plan.setApprover(approver);
        plan.setApprovalTime(LocalDateTime.now());

        plan = purchasePlanRepository.save(plan);
        log.info("Approved purchase plan: planNo={}, approver={}", plan.getPlanNo(), approver);

        return plan;
    }

    @Transactional
    public PurchasePlan rejectPlan(Long planId, String approver, String reason) {
        PurchasePlan plan = purchasePlanRepository.findById(planId)
                .orElseThrow(() -> new IllegalArgumentException("Purchase plan not found: " + planId));

        plan.setApprovalStatus(ApprovalStatus.REJECTED);
        plan.setStatus(PurchaseStatus.CANCELLED);
        plan.setApprover(approver);
        plan.setApprovalTime(LocalDateTime.now());
        plan.setRemark(reason);

        plan = purchasePlanRepository.save(plan);
        log.info("Rejected purchase plan: planNo={}, approver={}", plan.getPlanNo(), approver);

        return plan;
    }

    @Transactional
    public PurchasePlan placeOrder(Long planId) {
        PurchasePlan plan = purchasePlanRepository.findById(planId)
                .orElseThrow(() -> new IllegalArgumentException("Purchase plan not found: " + planId));

        if (plan.getApprovalStatus() != ApprovalStatus.APPROVED) {
            throw new IllegalStateException("Plan must be approved before placing order");
        }

        plan.setStatus(PurchaseStatus.ORDERED);
        plan.setOrderDate(LocalDateTime.now());
        if (plan.getExpectedDate() == null) {
            plan.setExpectedDate(LocalDate.now().plusDays(plan.getLeadTimeDays() != null ? plan.getLeadTimeDays() : 14));
        }

        plan = purchasePlanRepository.save(plan);
        log.info("Placed order for purchase plan: planNo={}", plan.getPlanNo());

        return plan;
    }

    @Transactional
    public PurchasePlan confirmReceipt(Long planId, Integer actualQuantity) {
        PurchasePlan plan = purchasePlanRepository.findById(planId)
                .orElseThrow(() -> new IllegalArgumentException("Purchase plan not found: " + planId));

        plan.setStatus(PurchaseStatus.RECEIVED);
        plan.setActualQuantity(actualQuantity);
        plan.setReceiptDate(LocalDateTime.now());

        plan = purchasePlanRepository.save(plan);
        log.info("Confirmed receipt for purchase plan: planNo={}, actualQuantity={}",
                plan.getPlanNo(), actualQuantity);

        redisCacheService.evictStockCache(plan.getWarehouseId(), plan.getMedicineId());
        redisCacheService.evictReorderPointCache(plan.getWarehouseId(), plan.getMedicineId());

        return plan;
    }

    @Transactional
    public PurchasePlan cancelPlan(Long planId, String reason) {
        PurchasePlan plan = purchasePlanRepository.findById(planId)
                .orElseThrow(() -> new IllegalArgumentException("Purchase plan not found: " + planId));

        plan.setStatus(PurchaseStatus.CANCELLED);
        plan.setRemark(reason);

        plan = purchasePlanRepository.save(plan);
        log.info("Cancelled purchase plan: planNo={}", plan.getPlanNo());

        return plan;
    }

    public boolean hasActivePurchasePlan(Long warehouseId, Long medicineId) {
        List<PurchaseStatus> activeStatuses = List.of(
                PurchaseStatus.PENDING, PurchaseStatus.APPROVED,
                PurchaseStatus.ORDERED, PurchaseStatus.IN_TRANSIT
        );
        Long count = purchasePlanRepository.countActivePlans(warehouseId, medicineId, activeStatuses);
        return count > 0;
    }

    public List<PurchasePlan> getPlansByStatus(PurchaseStatus status) {
        return purchasePlanRepository.findByStatus(status);
    }

    public List<PurchasePlan> getPlansByApprovalStatus(ApprovalStatus approvalStatus) {
        return purchasePlanRepository.findByApprovalStatus(approvalStatus);
    }

    public List<PurchasePlan> getPendingApprovalPlans() {
        return purchasePlanRepository.findByApprovalStatus(ApprovalStatus.PENDING);
    }

    public List<PurchasePlan> getPlansByWarehouse(Long warehouseId) {
        return purchasePlanRepository.findByWarehouseIdAndStatus(warehouseId, PurchaseStatus.PENDING);
    }

    public PurchasePlan getPlanById(Long planId) {
        return purchasePlanRepository.findById(planId)
                .orElseThrow(() -> new IllegalArgumentException("Purchase plan not found: " + planId));
    }

    public List<PurchasePlan> getPlansByDateRange(LocalDate startDate, LocalDate endDate) {
        return purchasePlanRepository.findByPlanDateBetween(startDate, endDate);
    }

    private PurchasePlanDTO buildPurchasePlanDTO(ReorderPointDTO reorderPoint) {
        Medicine medicine = medicineRepository.findById(reorderPoint.getMedicineId()).orElse(null);
        Warehouse warehouse = warehouseRepository.findById(reorderPoint.getWarehouseId()).orElse(null);

        int quantity = reorderPoint.getMaxStock() - reorderPoint.getCurrentStock();
        quantity = Math.max(quantity, 1);

        return PurchasePlanDTO.builder()
                .medicineId(reorderPoint.getMedicineId())
                .medicineName(medicine != null ? medicine.getMedicineName() : null)
                .warehouseId(reorderPoint.getWarehouseId())
                .warehouseName(warehouse != null ? warehouse.getWarehouseName() : null)
                .planQuantity(quantity)
                .expectedDate(LocalDate.now().plusDays(reorderPoint.getLeadTimeDays()))
                .reorderPoint(reorderPoint.getReorderPoint())
                .safetyStock(reorderPoint.getSafetyStock())
                .avgConsumption(reorderPoint.getAvgDailyConsumption())
                .leadTimeDays(reorderPoint.getLeadTimeDays())
                .remark("Auto-generated by system due to low stock")
                .build();
    }

    private String generatePlanNo() {
        String timestamp = LocalDateTime.now().format(PLAN_NO_FORMATTER);
        int random = new Random().nextInt(1000);
        return "PO" + timestamp + String.format("%03d", random);
    }
}
