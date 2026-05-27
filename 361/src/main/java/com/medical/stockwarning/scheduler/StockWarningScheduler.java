package com.medical.stockwarning.scheduler;

import com.medical.stockwarning.entity.PurchasePlan;
import com.medical.stockwarning.optimization.StockAllocationOptimizer;
import com.medical.stockwarning.service.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class StockWarningScheduler {

    private final ReorderCalculationService reorderCalculationService;
    private final PurchasePlanService purchasePlanService;
    private final ExpiryWarningService expiryWarningService;
    private final StockAllocationOptimizer allocationOptimizer;
    private final WarningService warningService;
    private final RedisCacheService redisCacheService;

    @Scheduled(cron = "${app.stock.warning-check-cron:0 0 2 * * ?}")
    public void checkStockWarnings() {
        log.info("Starting scheduled stock warning check...");

        if (!redisCacheService.acquireLock("warning-check", "scheduler")) {
            log.info("Warning check is already running, skipping this execution");
            return;
        }

        try {
            reorderCalculationService.refreshCache();

            List<PurchasePlan> plans = purchasePlanService.generatePurchasePlansForLowStock();
            log.info("Generated {} purchase plans for low stock items", plans.size());

            List<StockAllocationOptimizer.OptimizationResult> allocations = allocationOptimizer.optimizeAllMedicines();
            log.info("Generated {} allocation plans for stock optimization", allocations.size());

            log.info("Scheduled stock warning check completed successfully");
        } catch (Exception e) {
            log.error("Error during scheduled stock warning check: {}", e.getMessage(), e);
        } finally {
            redisCacheService.releaseLock("warning-check", "scheduler");
        }
    }

    @Scheduled(cron = "${app.stock.expiry-check-cron:0 0 3 * * ?}")
    public void checkExpiryWarnings() {
        log.info("Starting scheduled expiry check...");

        if (!redisCacheService.acquireLock("expiry-check", "scheduler")) {
            log.info("Expiry check is already running, skipping this execution");
            return;
        }

        try {
            expiryWarningService.runFullExpiryCheck();
            log.info("Scheduled expiry check completed successfully");
        } catch (Exception e) {
            log.error("Error during scheduled expiry check: {}", e.getMessage(), e);
        } finally {
            redisCacheService.releaseLock("expiry-check", "scheduler");
        }
    }

    @Scheduled(cron = "0 0 4 * * ?")
    public void refreshAllCaches() {
        log.info("Starting scheduled cache refresh...");

        try {
            redisCacheService.evictAllStockCache();
            redisCacheService.evictAllReorderPointCache();
            log.info("Scheduled cache refresh completed successfully");
        } catch (Exception e) {
            log.error("Error during cache refresh: {}", e.getMessage(), e);
        }
    }

    @Scheduled(cron = "0 30 1 * * ?")
    public void cleanOldWarnings() {
        log.info("Starting scheduled warning cleanup...");

        try {
            long unresolvedCount = warningService.countUnresolvedWarnings();
            log.info("Current unresolved warnings: {}", unresolvedCount);
            log.info("Scheduled warning cleanup completed");
        } catch (Exception e) {
            log.error("Error during warning cleanup: {}", e.getMessage(), e);
        }
    }
}
