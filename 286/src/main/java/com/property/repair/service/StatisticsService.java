package com.property.repair.service;

import com.property.repair.repository.RepairOrderRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigInteger;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class StatisticsService {

    @Autowired
    private RepairOrderRepository orderRepository;

    public Map<String, Object> getOverview() {
        Map<String, Object> result = new HashMap<>();

        result.put("pendingCount", orderRepository.countByStatus("PENDING"));
        result.put("assignedCount", orderRepository.countByStatus("ASSIGNED"));
        result.put("inProgressCount", orderRepository.countByStatus("IN_PROGRESS"));
        result.put("completedCount", orderRepository.countByStatus("COMPLETED"));
        result.put("evaluatedCount", orderRepository.countByStatus("EVALUATED"));

        return result;
    }

    public Map<String, Long> getTypeStatistics() {
        Map<String, Long> result = new HashMap<>();
        List<Object[]> stats = orderRepository.countByRepairType();
        for (Object[] row : stats) {
            String typeName = (String) row[0];
            Long count = ((Number) row[1]).longValue();
            result.put(typeName, count);
        }
        return result;
    }

    public Map<String, Long> getDailyStatistics(int days) {
        Map<String, Long> result = new HashMap<>();
        LocalDateTime startTime = LocalDateTime.now().minusDays(days);
        List<Object[]> stats = orderRepository.countByDate(startTime);
        for (Object[] row : stats) {
            String date = row[0].toString();
            Long count = ((Number) row[1]).longValue();
            result.put(date, count);
        }
        return result;
    }

    public List<Map<String, Object>> getWorkerStatistics() {
        List<Object[]> stats = orderRepository.getWorkerStats();
        return stats.stream().map(row -> {
            Map<String, Object> map = new HashMap<>();
            map.put("workerId", row[0]);
            map.put("workerName", row[1]);
            map.put("orderCount", row[2]);
            map.put("avgRating", row[3]);
            return map;
        }).collect(java.util.stream.Collectors.toList());
    }
}
