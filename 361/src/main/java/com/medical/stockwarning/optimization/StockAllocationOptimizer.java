package com.medical.stockwarning.optimization;

import com.google.ortools.Loader;
import com.google.ortools.linearsolver.MPConstraint;
import com.google.ortools.linearsolver.MPObjective;
import com.google.ortools.linearsolver.MPSolver;
import com.google.ortools.linearsolver.MPVariable;
import com.medical.stockwarning.dto.StockAllocationDTO;
import com.medical.stockwarning.entity.Medicine;
import com.medical.stockwarning.entity.Stock;
import com.medical.stockwarning.entity.Warehouse;
import com.medical.stockwarning.repository.MedicineRepository;
import com.medical.stockwarning.repository.StockRepository;
import com.medical.stockwarning.repository.WarehouseRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class StockAllocationOptimizer {

    private final StockRepository stockRepository;
    private final MedicineRepository medicineRepository;
    private final WarehouseRepository warehouseRepository;

    @Value("${app.stock.optimization.enable-ortools:true}")
    private boolean enableOrTools;

    @Value("${app.stock.optimization.solver-time-limit-seconds:30}")
    private int solverTimeLimitSeconds;

    @Value("${app.stock.optimization.unit-transport-cost:1.0}")
    private double unitTransportCost;

    @Value("${app.stock.optimization.distance-cost-weight:0.5}")
    private double distanceCostWeight;

    static {
        try {
            Loader.loadNativeLibraries();
        } catch (Exception e) {
            log.warn("OR-Tools native libraries not available, will use fallback heuristic: {}", e.getMessage());
        }
    }

    public OptimizationResult optimizeAllocation(Long medicineId) {
        Medicine medicine = medicineRepository.findById(medicineId)
                .orElseThrow(() -> new IllegalArgumentException("Medicine not found: " + medicineId));

        List<Warehouse> warehouses = warehouseRepository.findByStatus(1);
        if (warehouses.size() < 2) {
            log.info("Need at least 2 warehouses for optimization, found: {}", warehouses.size());
            return OptimizationResult.empty();
        }

        List<WarehouseInfo> warehouseInfos = new ArrayList<>();
        List<Integer> demands = new ArrayList<>();
        List<Integer> supplies = new ArrayList<>();
        double[][] distanceMatrix = calculateDistanceMatrix(warehouses);
        double[][] unitCostMatrix = calculateUnitCostMatrix(warehouses, distanceMatrix);

        for (Warehouse warehouse : warehouses) {
            Integer availableStock = stockRepository.sumAvailableQuantity(warehouse.getId(), medicineId);
            availableStock = availableStock != null ? availableStock : 0;

            Integer totalStock = stockRepository.sumTotalQuantity(warehouse.getId(), medicineId);
            totalStock = totalStock != null ? totalStock : 0;

            BigDecimal unitPrice = getAverageUnitPrice(warehouse.getId(), medicineId);

            int safetyStock = (int) (totalStock * 0.2);
            int excessStock = Math.max(availableStock - safetyStock, 0);
            int deficitStock = Math.max(safetyStock - availableStock, 0);

            WarehouseInfo info = WarehouseInfo.builder()
                    .warehouseId(warehouse.getId())
                    .warehouseName(warehouse.getWarehouseName())
                    .availableStock(availableStock)
                    .safetyStock(safetyStock)
                    .excessStock(excessStock)
                    .deficitStock(deficitStock)
                    .unitPrice(unitPrice)
                    .build();

            warehouseInfos.add(info);
            supplies.add(excessStock);
            demands.add(deficitStock);
        }

        int totalExcess = supplies.stream().mapToInt(Integer::intValue).sum();
        int totalDeficit = demands.stream().mapToInt(Integer::intValue).sum();

        if (totalExcess == 0 || totalDeficit == 0) {
            log.info("No allocation needed: totalExcess={}, totalDeficit={}", totalExcess, totalDeficit);
            return OptimizationResult.empty();
        }

        List<StockAllocationDTO> allocations;
        double totalCost;

        if (enableOrTools) {
            AllocationResult result = solveWithOrTools(warehouseInfos, supplies, demands, unitCostMatrix, medicine);
            allocations = result.getAllocations();
            totalCost = result.getTotalCost();
        } else {
            AllocationResult result = solveWithHeuristic(warehouseInfos, supplies, demands, unitCostMatrix, medicine);
            allocations = result.getAllocations();
            totalCost = result.getTotalCost();
        }

        log.info("Optimization result: medicine={}, allocations={}, totalCost={}", medicine.getMedicineName(), allocations.size(), totalCost);

        return OptimizationResult.builder()
                .medicineId(medicineId)
                .medicineName(medicine.getMedicineName())
                .allocations(allocations)
                .totalAllocated(allocations.stream().mapToInt(StockAllocationDTO::getQuantity).sum())
                .totalCost(totalCost)
                .build();
    }

    private double[][] calculateDistanceMatrix(List<Warehouse> warehouses) {
        int n = warehouses.size();
        double[][] distance = new double[n][n];

        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                if (i == j) {
                    distance[i][j] = 0;
                } else {
                    distance[i][j] = calculateDistance(warehouses.get(i), warehouses.get(j));
                }
            }
        }

        return distance;
    }

    private double calculateDistance(Warehouse w1, Warehouse w2) {
        if (w1.getLocation() == null || w2.getLocation() == null) {
            return 10.0;
        }
        return 10.0 + new Random(w1.getId() * 1000 + w2.getId()).nextDouble() * 50.0;
    }

    private double[][] calculateUnitCostMatrix(List<Warehouse> warehouses, double[][] distanceMatrix) {
        int n = warehouses.size();
        double[][] cost = new double[n][n];

        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                if (i == j) {
                    cost[i][j] = 0;
                } else {
                    double transportCost = unitTransportCost * distanceMatrix[i][j] * distanceCostWeight;
                    cost[i][j] = transportCost;
                }
            }
        }

        return cost;
    }

    private BigDecimal getAverageUnitPrice(Long warehouseId, Long medicineId) {
        List<Stock> stocks = stockRepository.findByWarehouseIdAndMedicineId(warehouseId, medicineId);
        if (stocks.isEmpty()) {
            return BigDecimal.ZERO;
        }
        return stocks.stream()
                .map(Stock::getUnitPrice)
                .filter(Objects::nonNull)
                .reduce(BigDecimal.ZERO, BigDecimal::add)
                .divide(BigDecimal.valueOf(stocks.size()), 2, BigDecimal.ROUND_HALF_UP);
    }

    private AllocationResult solveWithOrTools(List<WarehouseInfo> warehouses,
                                               List<Integer> supplies,
                                               List<Integer> demands,
                                               double[][] unitCostMatrix,
                                               Medicine medicine) {
        try {
            MPSolver solver = MPSolver.createSolver("SCIP");
            if (solver == null) {
                log.warn("SCIP solver not available, falling back to heuristic");
                return solveWithHeuristic(warehouses, supplies, demands, unitCostMatrix, medicine);
            }

            solver.setTimeLimit(solverTimeLimitSeconds * 1000L);

            int n = warehouses.size();
            MPVariable[][] x = new MPVariable[n][n];
            for (int i = 0; i < n; i++) {
                for (int j = 0; j < n; j++) {
                    if (i != j && supplies.get(i) > 0 && demands.get(j) > 0) {
                        x[i][j] = solver.makeIntVar(0, Math.min(supplies.get(i), demands.get(j)),
                                "x_" + i + "_" + j);
                    }
                }
            }

            MPObjective objective = solver.objective();
            for (int i = 0; i < n; i++) {
                for (int j = 0; j < n; j++) {
                    if (x[i][j] != null) {
                        objective.setCoefficient(x[i][j], unitCostMatrix[i][j]);
                    }
                }
            }
            objective.setMinimization();

            for (int i = 0; i < n; i++) {
                if (supplies.get(i) > 0) {
                    MPConstraint supplyConstraint = solver.makeConstraint(0, supplies.get(i), "supply_" + i);
                    for (int j = 0; j < n; j++) {
                        if (x[i][j] != null) {
                            supplyConstraint.setCoefficient(x[i][j], 1);
                        }
                    }
                }
            }

            for (int j = 0; j < n; j++) {
                if (demands.get(j) > 0) {
                    MPConstraint demandConstraint = solver.makeConstraint(0, demands.get(j), "demand_" + j);
                    for (int i = 0; i < n; i++) {
                        if (x[i][j] != null) {
                            demandConstraint.setCoefficient(x[i][j], 1);
                        }
                    }
                }
            }

            MPSolver.ResultStatus status = solver.solve();

            if (status == MPSolver.ResultStatus.OPTIMAL || status == MPSolver.ResultStatus.FEASIBLE) {
                List<StockAllocationDTO> allocations = new ArrayList<>();
                double totalCost = objective.value();

                for (int i = 0; i < n; i++) {
                    for (int j = 0; j < n; j++) {
                        if (x[i][j] != null && x[i][j].solutionValue() > 0) {
                            int quantity = (int) x[i][j].solutionValue();
                            WarehouseInfo from = warehouses.get(i);
                            WarehouseInfo to = warehouses.get(j);
                            double cost = unitCostMatrix[i][j] * quantity;

                            StockAllocationDTO dto = StockAllocationDTO.builder()
                                    .medicineId(medicine.getId())
                                    .medicineName(medicine.getMedicineName())
                                    .fromWarehouseId(from.getWarehouseId())
                                    .fromWarehouseName(from.getWarehouseName())
                                    .toWarehouseId(to.getWarehouseId())
                                    .toWarehouseName(to.getWarehouseName())
                                    .quantity(quantity)
                                    .unitPrice(from.getUnitPrice())
                                    .totalAmount(from.getUnitPrice().multiply(BigDecimal.valueOf(quantity)))
                                    .reason(String.format("Optimized allocation via OR-Tools (cost: %.2f)", cost))
                                    .build();

                            allocations.add(dto);
                        }
                    }
                }

                log.info("OR-Tools optimization completed, objective value: {}", totalCost);
                return new AllocationResult(allocations, totalCost);
            } else {
                log.warn("OR-Tools solver status: {}, falling back to heuristic", status);
                return solveWithHeuristic(warehouses, supplies, demands, unitCostMatrix, medicine);
            }
        } catch (Exception e) {
            log.error("OR-Tools optimization failed, falling back to heuristic: {}", e.getMessage());
            return solveWithHeuristic(warehouses, supplies, demands, unitCostMatrix, medicine);
        }
    }

    private AllocationResult solveWithHeuristic(List<WarehouseInfo> warehouses,
                                                 List<Integer> supplies,
                                                 List<Integer> demands,
                                                 double[][] unitCostMatrix,
                                                 Medicine medicine) {
        List<StockAllocationDTO> allocations = new ArrayList<>();
        double totalCost = 0;

        List<WarehouseInfo> suppliers = warehouses.stream()
                .filter(w -> w.getExcessStock() > 0)
                .sorted(Comparator.comparingInt(WarehouseInfo::getExcessStock).reversed())
                .toList();

        List<WarehouseInfo> demanders = warehouses.stream()
                .filter(w -> w.getDeficitStock() > 0)
                .sorted(Comparator.comparingInt(WarehouseInfo::getDeficitStock).reversed())
                .toList();

        Map<Long, Integer> supplierIndexMap = new HashMap<>();
        Map<Long, Integer> demanderIndexMap = new HashMap<>();
        for (int i = 0; i < warehouses.size(); i++) {
            if (warehouses.get(i).getExcessStock() > 0) {
                supplierIndexMap.put(warehouses.get(i).getWarehouseId(), i);
            }
            if (warehouses.get(i).getDeficitStock() > 0) {
                demanderIndexMap.put(warehouses.get(i).getWarehouseId(), i);
            }
        }

        for (WarehouseInfo demander : demanders) {
            int remainingDeficit = demander.getDeficitStock();

            List<WarehouseInfo> sortedSuppliers = new ArrayList<>(suppliers);
            sortedSuppliers.sort((s1, s2) -> {
                int idx1 = supplierIndexMap.getOrDefault(s1.getWarehouseId(), 0);
                int idx2 = supplierIndexMap.getOrDefault(s2.getWarehouseId(), 0);
                int demanderIdx = demanderIndexMap.getOrDefault(demander.getWarehouseId(), 0);
                return Double.compare(unitCostMatrix[idx1][demanderIdx], unitCostMatrix[idx2][demanderIdx]);
            });

            for (WarehouseInfo supplier : sortedSuppliers) {
                if (remainingDeficit <= 0) break;
                if (supplier.getExcessStock() <= 0) continue;

                int quantity = Math.min(supplier.getExcessStock(), remainingDeficit);
                if (quantity > 0) {
                    int supplierIdx = supplierIndexMap.getOrDefault(supplier.getWarehouseId(), 0);
                    int demanderIdx = demanderIndexMap.getOrDefault(demander.getWarehouseId(), 0);
                    double cost = unitCostMatrix[supplierIdx][demanderIdx] * quantity;
                    totalCost += cost;

                    StockAllocationDTO dto = StockAllocationDTO.builder()
                            .medicineId(medicine.getId())
                            .medicineName(medicine.getMedicineName())
                            .fromWarehouseId(supplier.getWarehouseId())
                            .fromWarehouseName(supplier.getWarehouseName())
                            .toWarehouseId(demander.getWarehouseId())
                            .toWarehouseName(demander.getWarehouseName())
                            .quantity(quantity)
                            .unitPrice(supplier.getUnitPrice())
                            .totalAmount(supplier.getUnitPrice().multiply(BigDecimal.valueOf(quantity)))
                            .reason(String.format("Cost-optimized heuristic allocation (cost: %.2f)", cost))
                            .build();

                    allocations.add(dto);

                    supplier.setExcessStock(supplier.getExcessStock() - quantity);
                    remainingDeficit -= quantity;
                }
            }
        }

        return new AllocationResult(allocations, totalCost);
    }

    public List<OptimizationResult> optimizeAllMedicines() {
        List<Medicine> medicines = medicineRepository.findByIsActive(1);
        List<OptimizationResult> results = new ArrayList<>();

        for (Medicine medicine : medicines) {
            try {
                OptimizationResult result = optimizeAllocation(medicine.getId());
                if (!result.getAllocations().isEmpty()) {
                    results.add(result);
                }
            } catch (Exception e) {
                log.error("Error optimizing allocation for medicine {}: {}",
                        medicine.getMedicineName(), e.getMessage());
            }
        }

        return results;
    }

    private static class AllocationResult {
        private final List<StockAllocationDTO> allocations;
        private final double totalCost;

        public AllocationResult(List<StockAllocationDTO> allocations, double totalCost) {
            this.allocations = allocations;
            this.totalCost = totalCost;
        }

        public List<StockAllocationDTO> getAllocations() {
            return allocations;
        }

        public double getTotalCost() {
            return totalCost;
        }
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class WarehouseInfo {
        private Long warehouseId;
        private String warehouseName;
        private Integer availableStock;
        private Integer safetyStock;
        private Integer excessStock;
        private Integer deficitStock;
        private BigDecimal unitPrice;
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class OptimizationResult {
        private Long medicineId;
        private String medicineName;
        private List<StockAllocationDTO> allocations;
        private Integer totalAllocated;
        private Double totalCost;

        public static OptimizationResult empty() {
            return OptimizationResult.builder()
                    .allocations(Collections.emptyList())
                    .totalAllocated(0)
                    .totalCost(0.0)
                    .build();
        }
    }
}
