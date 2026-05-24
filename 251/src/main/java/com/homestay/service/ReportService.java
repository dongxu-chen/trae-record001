package com.homestay.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.homestay.common.BusinessException;
import com.homestay.common.UserContext;
import com.homestay.entity.House;
import com.homestay.entity.HouseDailyStats;
import com.homestay.entity.Review;
import com.homestay.entity.User;
import com.homestay.mapper.HouseDailyStatsMapper;
import com.homestay.mapper.HouseMapper;
import com.homestay.mapper.ReviewMapper;
import com.homestay.mapper.UserMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class ReportService {

    @Autowired
    private HouseDailyStatsMapper houseDailyStatsMapper;

    @Autowired
    private HouseMapper houseMapper;

    @Autowired
    private UserMapper userMapper;

    @Autowired
    private ReviewMapper reviewMapper;

    public Map<String, Object> getHostReport(LocalDate startDate, LocalDate endDate) {
        Long hostId = UserContext.getUserId();
        if (hostId == null) {
            throw new BusinessException("请先登录");
        }
        User host = userMapper.selectById(hostId);
        if (host == null || host.getHostStatus() != 1) {
            throw new BusinessException("请先成为房东");
        }

        if (startDate == null) {
            startDate = LocalDate.now().minusDays(30);
        }
        if (endDate == null) {
            endDate = LocalDate.now();
        }

        Map<String, Object> result = new HashMap<>();

        Map<String, Object> summary = houseDailyStatsMapper.getHostSummary(hostId, startDate, endDate);
        if (summary == null) {
            summary = new HashMap<>();
        }
        result.put("summary", convertToBigDecimal(summary));

        List<House> houses = houseMapper.selectList(new LambdaQueryWrapper<House>()
                .eq(House::getHostId, hostId)
                .eq(House::getDeleted, 0));
        result.put("houseCount", houses.size());

        List<Map<String, Object>> dailyStats = houseDailyStatsMapper.getHostDailyStats(hostId, startDate, endDate);
        result.put("dailyTrend", dailyStats);

        Map<String, Object> incomeTrend = generateIncomeTrend(dailyStats, startDate, endDate);
        result.put("incomeTrend", incomeTrend);

        Map<String, Object> occupancyTrend = generateOccupancyTrend(dailyStats, startDate, endDate);
        result.put("occupancyTrend", occupancyTrend);

        Map<String, Object> reviewAnalysis = getReviewAnalysis(hostId, startDate, endDate);
        result.put("reviewAnalysis", reviewAnalysis);

        List<Map<String, Object>> houseRankings = getHouseRankings(hostId, startDate, endDate);
        result.put("houseRankings", houseRankings);

        Map<String, Object> weekAnalysis = getWeekAnalysis(dailyStats);
        result.put("weekAnalysis", weekAnalysis);

        return result;
    }

    public Map<String, Object> getHouseReport(Long houseId, LocalDate startDate, LocalDate endDate) {
        Long hostId = UserContext.getUserId();
        House house = houseMapper.selectById(houseId);
        if (house == null) {
            throw new BusinessException("房源不存在");
        }
        if (!house.getHostId().equals(hostId)) {
            throw new BusinessException("无权限查看该房源报表");
        }

        if (startDate == null) {
            startDate = LocalDate.now().minusDays(30);
        }
        if (endDate == null) {
            endDate = LocalDate.now();
        }

        Map<String, Object> result = new HashMap<>();
        result.put("houseId", houseId);
        result.put("houseTitle", house.getTitle());

        Map<String, Object> summary = houseDailyStatsMapper.getHouseSummary(houseId, startDate, endDate);
        if (summary == null) {
            summary = new HashMap<>();
        }
        result.put("summary", convertToBigDecimal(summary));

        List<Map<String, Object>> dailyStats = houseDailyStatsMapper.getHouseDailyStats(houseId, startDate, endDate);
        result.put("dailyTrend", dailyStats);

        Map<String, Object> incomeTrend = generateIncomeTrend(dailyStats, startDate, endDate);
        result.put("incomeTrend", incomeTrend);

        Map<String, Object> occupancyTrend = generateOccupancyTrend(dailyStats, startDate, endDate);
        result.put("occupancyTrend", occupancyTrend);

        Map<String, Object> reviewAnalysis = getHouseReviewAnalysis(houseId, startDate, endDate);
        result.put("reviewAnalysis", reviewAnalysis);

        return result;
    }

    private Map<String, Object> convertToBigDecimal(Map<String, Object> map) {
        Map<String, Object> result = new HashMap<>();
        for (Map.Entry<String, Object> entry : map.entrySet()) {
            Object value = entry.getValue();
            if (value instanceof Number) {
                result.put(entry.getKey(), new BigDecimal(value.toString()).setScale(2, RoundingMode.HALF_UP));
            } else {
                result.put(entry.getKey(), value);
            }
        }
        return result;
    }

    private Map<String, Object> generateIncomeTrend(List<Map<String, Object>> dailyStats, LocalDate startDate, LocalDate endDate) {
        Map<String, Object> trend = new HashMap<>();
        List<String> dates = new ArrayList<>();
        List<BigDecimal> incomes = new ArrayList<>();

        Map<LocalDate, BigDecimal> incomeMap = new HashMap<>();
        for (Map<String, Object> stat : dailyStats) {
            LocalDate date = (LocalDate) stat.get("stat_date");
            BigDecimal income = stat.get("total_income") != null
                    ? new BigDecimal(stat.get("total_income").toString())
                    : BigDecimal.ZERO;
            incomeMap.put(date, income);
        }

        for (LocalDate date = startDate; !date.isAfter(endDate); date = date.plusDays(1)) {
            dates.add(date.toString());
            incomes.add(incomeMap.getOrDefault(date, BigDecimal.ZERO).setScale(2, RoundingMode.HALF_UP));
        }

        trend.put("dates", dates);
        trend.put("incomes", incomes);

        BigDecimal total = incomes.stream().reduce(BigDecimal.ZERO, BigDecimal::add);
        BigDecimal avg = incomes.isEmpty() ? BigDecimal.ZERO : total.divide(BigDecimal.valueOf(incomes.size()), 2, RoundingMode.HALF_UP);
        trend.put("total", total);
        trend.put("avg", avg);
        trend.put("max", incomes.stream().max(BigDecimal::compareTo).orElse(BigDecimal.ZERO));
        trend.put("min", incomes.stream().min(BigDecimal::compareTo).orElse(BigDecimal.ZERO));

        return trend;
    }

    private Map<String, Object> generateOccupancyTrend(List<Map<String, Object>> dailyStats, LocalDate startDate, LocalDate endDate) {
        Map<String, Object> trend = new HashMap<>();
        List<String> dates = new ArrayList<>();
        List<BigDecimal> rates = new ArrayList<>();

        Map<LocalDate, BigDecimal> rateMap = new HashMap<>();
        for (Map<String, Object> stat : dailyStats) {
            LocalDate date = (LocalDate) stat.get("stat_date");
            BigDecimal rate = stat.get("occupancy_rate") != null
                    ? new BigDecimal(stat.get("occupancy_rate").toString())
                    : BigDecimal.ZERO;
            rateMap.put(date, rate);
        }

        for (LocalDate date = startDate; !date.isAfter(endDate); date = date.plusDays(1)) {
            dates.add(date.toString());
            rates.add(rateMap.getOrDefault(date, BigDecimal.ZERO).setScale(4, RoundingMode.HALF_UP));
        }

        trend.put("dates", dates);
        trend.put("rates", rates);

        BigDecimal avg = rates.isEmpty() ? BigDecimal.ZERO : rates.stream()
                .reduce(BigDecimal.ZERO, BigDecimal::add)
                .divide(BigDecimal.valueOf(rates.size()), 4, RoundingMode.HALF_UP);
        trend.put("avgRate", avg);
        trend.put("avgRatePercent", avg.multiply(new BigDecimal("100")).setScale(2, RoundingMode.HALF_UP) + "%");

        return trend;
    }

    private Map<String, Object> getReviewAnalysis(Long hostId, LocalDate startDate, LocalDate endDate) {
        Map<String, Object> analysis = new HashMap<>();

        List<Review> reviews = reviewMapper.selectList(new LambdaQueryWrapper<Review>()
                .eq(Review::getHostId, hostId)
                .between(Review::getCreateTime, startDate.atStartOfDay(), endDate.atTime(23, 59, 59)));

        analysis.put("totalReviews", reviews.size());

        if (!reviews.isEmpty()) {
            double avgRating = reviews.stream()
                    .mapToInt(Review::getRating)
                    .average()
                    .orElse(0);
            analysis.put("avgRating", BigDecimal.valueOf(avgRating).setScale(2, RoundingMode.HALF_UP));

            Map<Integer, Long> ratingDistribution = reviews.stream()
                    .collect(Collectors.groupingBy(Review::getRating, Collectors.counting()));
            analysis.put("ratingDistribution", ratingDistribution);

            double avgCleanliness = reviews.stream()
                    .mapToInt(r -> r.getCleanliness() != null ? r.getCleanliness() : 0)
                    .average()
                    .orElse(0);
            double avgAccuracy = reviews.stream()
                    .mapToInt(r -> r.getAccuracy() != null ? r.getAccuracy() : 0)
                    .average()
                    .orElse(0);
            double avgCommunication = reviews.stream()
                    .mapToInt(r -> r.getCommunication() != null ? r.getCommunication() : 0)
                    .average()
                    .orElse(0);
            double avgLocation = reviews.stream()
                    .mapToInt(r -> r.getLocation() != null ? r.getLocation() : 0)
                    .average()
                    .orElse(0);
            double avgCheckIn = reviews.stream()
                    .mapToInt(r -> r.getCheckIn() != null ? r.getCheckIn() : 0)
                    .average()
                    .orElse(0);
            double avgValue = reviews.stream()
                    .mapToInt(r -> r.getValue() != null ? r.getValue() : 0)
                    .average()
                    .orElse(0);

            Map<String, Object> dimensionScores = new HashMap<>();
            dimensionScores.put("cleanliness", BigDecimal.valueOf(avgCleanliness).setScale(2, RoundingMode.HALF_UP));
            dimensionScores.put("accuracy", BigDecimal.valueOf(avgAccuracy).setScale(2, RoundingMode.HALF_UP));
            dimensionScores.put("communication", BigDecimal.valueOf(avgCommunication).setScale(2, RoundingMode.HALF_UP));
            dimensionScores.put("location", BigDecimal.valueOf(avgLocation).setScale(2, RoundingMode.HALF_UP));
            dimensionScores.put("checkIn", BigDecimal.valueOf(avgCheckIn).setScale(2, RoundingMode.HALF_UP));
            dimensionScores.put("value", BigDecimal.valueOf(avgValue).setScale(2, RoundingMode.HALF_UP));
            analysis.put("dimensionScores", dimensionScores);

            long replyCount = reviews.stream()
                    .filter(r -> r.getHostReply() != null && !r.getHostReply().isEmpty())
                    .count();
            analysis.put("replyRate", BigDecimal.valueOf((double) replyCount / reviews.size() * 100)
                    .setScale(2, RoundingMode.HALF_UP) + "%");
        }

        return analysis;
    }

    private Map<String, Object> getHouseReviewAnalysis(Long houseId, LocalDate startDate, LocalDate endDate) {
        Map<String, Object> analysis = new HashMap<>();

        List<Review> reviews = reviewMapper.selectList(new LambdaQueryWrapper<Review>()
                .eq(Review::getHouseId, houseId)
                .between(Review::getCreateTime, startDate.atStartOfDay(), endDate.atTime(23, 59, 59)));

        analysis.put("totalReviews", reviews.size());

        if (!reviews.isEmpty()) {
            double avgRating = reviews.stream()
                    .mapToInt(Review::getRating)
                    .average()
                    .orElse(0);
            analysis.put("avgRating", BigDecimal.valueOf(avgRating).setScale(2, RoundingMode.HALF_UP));

            Map<Integer, Long> ratingDistribution = reviews.stream()
                    .collect(Collectors.groupingBy(Review::getRating, Collectors.counting()));
            analysis.put("ratingDistribution", ratingDistribution);
        }

        return analysis;
    }

    private List<Map<String, Object>> getHouseRankings(Long hostId, LocalDate startDate, LocalDate endDate) {
        List<House> houses = houseMapper.selectList(new LambdaQueryWrapper<House>()
                .eq(House::getHostId, hostId)
                .eq(House::getDeleted, 0));

        List<Map<String, Object>> rankings = new ArrayList<>();
        for (House house : houses) {
            Map<String, Object> summary = houseDailyStatsMapper.getHouseSummary(house.getId(), startDate, endDate);
            if (summary == null) {
                summary = new HashMap<>();
            }
            Map<String, Object> map = new HashMap<>();
            map.put("houseId", house.getId());
            map.put("title", house.getTitle());
            map.put("coverImage", house.getCoverImage());
            map.put("totalOrders", summary.getOrDefault("total_orders", 0));
            map.put("totalIncome", summary.getOrDefault("total_income", BigDecimal.ZERO));
            map.put("avgOccupancy", summary.getOrDefault("avg_occupancy", BigDecimal.ZERO));
            map.put("avgRating", house.getRating());
            rankings.add(map);
        }

        rankings.sort((a, b) -> {
            BigDecimal incomeA = (BigDecimal) a.get("totalIncome");
            BigDecimal incomeB = (BigDecimal) b.get("totalIncome");
            return incomeB.compareTo(incomeA);
        });

        return rankings;
    }

    private Map<String, Object> getWeekAnalysis(List<Map<String, Object>> dailyStats) {
        Map<String, Object> analysis = new HashMap<>();

        String[] weekDays = {"周一", "周二", "周三", "周四", "周五", "周六", "周日"};
        Map<String, List<BigDecimal>> weekIncome = new HashMap<>();
        Map<String, List<BigDecimal>> weekOccupancy = new HashMap<>();

        for (String day : weekDays) {
            weekIncome.put(day, new ArrayList<>());
            weekOccupancy.put(day, new ArrayList<>());
        }

        for (Map<String, Object> stat : dailyStats) {
            LocalDate date = (LocalDate) stat.get("stat_date");
            int dayOfWeek = date.getDayOfWeek().getValue() - 1;
            String dayName = weekDays[dayOfWeek];

            BigDecimal income = stat.get("total_income") != null
                    ? new BigDecimal(stat.get("total_income").toString())
                    : BigDecimal.ZERO;
            BigDecimal occupancy = stat.get("occupancy_rate") != null
                    ? new BigDecimal(stat.get("occupancy_rate").toString())
                    : BigDecimal.ZERO;

            weekIncome.get(dayName).add(income);
            weekOccupancy.get(dayName).add(occupancy);
        }

        Map<String, BigDecimal> avgIncomeByDay = new LinkedHashMap<>();
        Map<String, BigDecimal> avgOccupancyByDay = new LinkedHashMap<>();

        for (String day : weekDays) {
            List<BigDecimal> incomes = weekIncome.get(day);
            List<BigDecimal> occupancies = weekOccupancy.get(day);

            BigDecimal avgIncome = incomes.isEmpty() ? BigDecimal.ZERO : incomes.stream()
                    .reduce(BigDecimal.ZERO, BigDecimal::add)
                    .divide(BigDecimal.valueOf(incomes.size()), 2, RoundingMode.HALF_UP);
            BigDecimal avgOccupancy = occupancies.isEmpty() ? BigDecimal.ZERO : occupancies.stream()
                    .reduce(BigDecimal.ZERO, BigDecimal::add)
                    .divide(BigDecimal.valueOf(occupancies.size()), 4, RoundingMode.HALF_UP);

            avgIncomeByDay.put(day, avgIncome);
            avgOccupancyByDay.put(day, avgOccupancy);
        }

        analysis.put("avgIncomeByDay", avgIncomeByDay);
        analysis.put("avgOccupancyByDay", avgOccupancyByDay);

        String bestDay = avgIncomeByDay.entrySet().stream()
                .max(Map.Entry.comparingByValue())
                .map(Map.Entry::getKey)
                .orElse("-");
        String worstDay = avgIncomeByDay.entrySet().stream()
                .min(Map.Entry.comparingByValue())
                .map(Map.Entry::getKey)
                .orElse("-");

        analysis.put("bestIncomeDay", bestDay);
        analysis.put("worstIncomeDay", worstDay);

        return analysis;
    }
}
