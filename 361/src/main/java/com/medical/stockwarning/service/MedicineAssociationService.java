package com.medical.stockwarning.service;

import com.medical.stockwarning.dto.MedicineAssociationDTO;
import com.medical.stockwarning.entity.Medicine;
import com.medical.stockwarning.entity.ConsumptionHistory;
import com.medical.stockwarning.repository.ConsumptionHistoryRepository;
import com.medical.stockwarning.repository.MedicineRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class MedicineAssociationService {

    private final ConsumptionHistoryRepository consumptionHistoryRepository;
    private final MedicineRepository medicineRepository;

    @Value("${app.association.min-support:0.05}")
    private double minSupport;

    @Value("${app.association.min-confidence:0.3}")
    private double minConfidence;

    @Value("${app.association.min-lift:1.0}")
    private double minLift;

    @Value("${app.association.analysis-days:180}")
    private int analysisDays;

    @Value("${app.association.window-days:1}")
    private int windowDays;

    public List<MedicineAssociationDTO> analyzeAssociations() {
        return analyzeAssociations(null);
    }

    public List<MedicineAssociationDTO> analyzeAssociations(Long warehouseId) {
        log.info("Starting medicine association analysis, warehouseId={}", warehouseId);

        LocalDate endDate = LocalDate.now();
        LocalDate startDate = endDate.minusDays(analysisDays);

        List<ConsumptionHistory> allHistory;
        if (warehouseId != null) {
            allHistory = consumptionHistoryRepository
                    .findByWarehouseIdAndMedicineIdAndConsumptionDateBetween(
                            warehouseId, null, startDate, endDate);
        } else {
            allHistory = consumptionHistoryRepository.findAll();
            allHistory = allHistory.stream()
                    .filter(h -> !h.getConsumptionDate().isBefore(startDate) && !h.getConsumptionDate().isAfter(endDate))
                    .toList();
        }

        if (allHistory.size() < 10) {
            log.warn("Insufficient consumption data for association analysis: {} records", allHistory.size());
            return Collections.emptyList();
        }

        Map<String, Set<Long>> transactionMap = buildTransactions(allHistory);

        if (transactionMap.size() < 5) {
            log.warn("Insufficient transactions for association analysis: {} transactions", transactionMap.size());
            return Collections.emptyList();
        }

        List<Set<Long>> transactions = new ArrayList<>(transactionMap.values());
        int totalTransactions = transactions.size();

        Map<Long, Integer> medicineCounts = countMedicineOccurrences(transactions);

        List<MedicineAssociationDTO> associations = findPairAssociations(
                transactions, medicineCounts, totalTransactions);

        associations = associations.stream()
                .sorted(Comparator.comparing(MedicineAssociationDTO::getLift).reversed())
                .toList();

        log.info("Association analysis completed: found {} associations from {} transactions",
                associations.size(), totalTransactions);

        return associations;
    }

    public List<MedicineAssociationDTO> getStrongAssociations() {
        return analyzeAssociations().stream()
                .filter(MedicineAssociationDTO::getIsStrongAssociation)
                .toList();
    }

    public List<MedicineAssociationDTO> getAssociationsForMedicine(Long medicineId) {
        return analyzeAssociations().stream()
                .filter(a -> a.getMedicineId().equals(medicineId) || a.getAssociatedMedicineId().equals(medicineId))
                .sorted(Comparator.comparing(MedicineAssociationDTO::getConfidence).reversed())
                .toList();
    }

    public List<Long> getAssociatedMedicineIds(Long medicineId) {
        return getAssociationsForMedicine(medicineId).stream()
                .filter(a -> a.getIsStrongAssociation())
                .map(a -> a.getMedicineId().equals(medicineId) ? a.getAssociatedMedicineId() : a.getMedicineId())
                .distinct()
                .toList();
    }

    public List<List<Long>> findFrequentMedicineGroups() {
        List<MedicineAssociationDTO> associations = getStrongAssociations();

        Map<Long, Set<Long>> graph = new HashMap<>();
        for (MedicineAssociationDTO a : associations) {
            graph.computeIfAbsent(a.getMedicineId(), k -> new HashSet<>()).add(a.getAssociatedMedicineId());
            graph.computeIfAbsent(a.getAssociatedMedicineId(), k -> new HashSet<>()).add(a.getMedicineId());
        }

        List<List<Long>> groups = new ArrayList<>();
        Set<Long> visited = new HashSet<>();

        for (Long node : graph.keySet()) {
            if (!visited.contains(node)) {
                List<Long> group = findConnectedGroup(node, graph, visited);
                if (group.size() >= 2) {
                    groups.add(group);
                }
            }
        }

        groups.sort((g1, g2) -> g2.size() - g1.size());
        return groups;
    }

    public List<MedicineAssociationDTO> checkCombinedStockout(List<Long> medicineIds) {
        List<MedicineAssociationDTO> results = new ArrayList<>();
        List<MedicineAssociationDTO> allAssociations = getStrongAssociations();

        for (MedicineAssociationDTO assoc : allAssociations) {
            boolean medicineInList = medicineIds.contains(assoc.getMedicineId());
            boolean associatedInList = medicineIds.contains(assoc.getAssociatedMedicineId());

            if (medicineInList || associatedInList) {
                results.add(assoc);
            }
        }

        return results;
    }

    private Map<String, Set<Long>> buildTransactions(List<ConsumptionHistory> history) {
        Map<String, Set<Long>> transactions = new HashMap<>();

        for (ConsumptionHistory record : history) {
            String dateKey = record.getConsumptionDate().toString();
            String deptKey = record.getDepartment() != null ? record.getDepartment() : "GENERAL";
            String transactionKey = dateKey + "_" + deptKey;

            transactions.computeIfAbsent(transactionKey, k -> new HashSet<>())
                    .add(record.getMedicineId());
        }

        return transactions;
    }

    private Map<Long, Integer> countMedicineOccurrences(List<Set<Long>> transactions) {
        Map<Long, Integer> counts = new HashMap<>();
        for (Set<Long> transaction : transactions) {
            for (Long medicineId : transaction) {
                counts.merge(medicineId, 1, Integer::sum);
            }
        }
        return counts;
    }

    private List<MedicineAssociationDTO> findPairAssociations(
            List<Set<Long>> transactions,
            Map<Long, Integer> medicineCounts,
            int totalTransactions) {

        List<MedicineAssociationDTO> results = new ArrayList<>();

        List<Long> medicineIds = new ArrayList<>(medicineCounts.keySet());
        Map<Long, Medicine> medicineMap = medicineRepository.findActiveByIds(medicineIds)
                .stream()
                .collect(Collectors.toMap(Medicine::getId, m -> m));

        for (int i = 0; i < medicineIds.size(); i++) {
            for (int j = i + 1; j < medicineIds.size(); j++) {
                Long medA = medicineIds.get(i);
                Long medB = medicineIds.get(j);

                int countA = medicineCounts.get(medA);
                int countB = medicineCounts.get(medB);

                if (countA < 2 || countB < 2) {
                    continue;
                }

                int coOccurrence = 0;
                for (Set<Long> transaction : transactions) {
                    if (transaction.contains(medA) && transaction.contains(medB)) {
                        coOccurrence++;
                    }
                }

                if (coOccurrence == 0) {
                    continue;
                }

                double support = (double) coOccurrence / totalTransactions;
                if (support < minSupport) {
                    continue;
                }

                double confidenceAB = (double) coOccurrence / countA;
                double confidenceBA = (double) coOccurrence / countB;

                double expectedConfidence = (double) countB / totalTransactions;
                double lift = expectedConfidence > 0 ? confidenceAB / expectedConfidence : 0;

                if (confidenceAB < minConfidence && confidenceBA < minConfidence) {
                    continue;
                }

                boolean isStrong = lift >= minLift &&
                        (confidenceAB >= minConfidence || confidenceBA >= minConfidence);

                Medicine medicineA = medicineMap.get(medA);
                Medicine medicineB = medicineMap.get(medB);

                MedicineAssociationDTO dto = MedicineAssociationDTO.builder()
                        .medicineId(medA)
                        .medicineName(medicineA != null ? medicineA.getMedicineName() : "ID:" + medA)
                        .associatedMedicineId(medB)
                        .associatedMedicineName(medicineB != null ? medicineB.getMedicineName() : "ID:" + medB)
                        .coOccurrenceCount(coOccurrence)
                        .medicineOccurrenceCount(countA)
                        .associatedOccurrenceCount(countB)
                        .support(support)
                        .confidence(Math.max(confidenceAB, confidenceBA))
                        .lift(lift)
                        .associationCount(coOccurrence)
                        .isStrongAssociation(isStrong)
                        .build();

                results.add(dto);
            }
        }

        return results;
    }

    private List<Long> findConnectedGroup(Long start, Map<Long, Set<Long>> graph, Set<Long> visited) {
        List<Long> group = new ArrayList<>();
        Queue<Long> queue = new LinkedList<>();
        queue.add(start);
        visited.add(start);

        while (!queue.isEmpty()) {
            Long current = queue.poll();
            group.add(current);

            Set<Long> neighbors = graph.getOrDefault(current, Collections.emptySet());
            for (Long neighbor : neighbors) {
                if (!visited.contains(neighbor)) {
                    visited.add(neighbor);
                    queue.add(neighbor);
                }
            }
        }

        return group;
    }

    public Map<String, Object> getAssociationStats() {
        List<MedicineAssociationDTO> associations = analyzeAssociations();
        Map<String, Object> stats = new HashMap<>();

        stats.put("totalAssociations", associations.size());
        stats.put("strongAssociations", associations.stream().filter(MedicineAssociationDTO::getIsStrongAssociation).count());
        stats.put("frequentGroups", findFrequentMedicineGroups().size());
        stats.put("analysisDays", analysisDays);
        stats.put("minSupport", minSupport);
        stats.put("minConfidence", minConfidence);
        stats.put("minLift", minLift);

        return stats;
    }
}
