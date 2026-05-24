package com.homestay.task;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.homestay.entity.House;
import com.homestay.entity.HouseCalendar;
import com.homestay.entity.HouseDailyStats;
import com.homestay.entity.OrderInfo;
import com.homestay.entity.Review;
import com.homestay.mapper.HouseCalendarMapper;
import com.homestay.mapper.HouseDailyStatsMapper;
import com.homestay.mapper.HouseMapper;
import com.homestay.mapper.OrderInfoMapper;
import com.homestay.mapper.ReviewMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.List;

@Slf4j
@Component
public class StatsTask {

    @Autowired
    private HouseDailyStatsMapper houseDailyStatsMapper;

    @Autowired
    private OrderInfoMapper orderInfoMapper;

    @Autowired
    private HouseMapper houseMapper;

    @Autowired
    private ReviewMapper reviewMapper;

    @Autowired
    private HouseCalendarMapper houseCalendarMapper;

    @Scheduled(cron = "0 0 3 * * ?")
    @Transactional(rollbackFor = Exception.class)
    public void calculateYesterdayStats() {
        LocalDate yesterday = LocalDate.now().minusDays(1);
        log.info("开始计算 {} 的房源经营数据", yesterday);

        List<House> houses = houseMapper.selectList(new LambdaQueryWrapper<House>()
                .eq(House::getDeleted, 0));

        for (House house : houses) {
            try {
                calculateHouseDailyStats(house.getId(), house.getHostId(), yesterday);
            } catch (Exception e) {
                log.error("计算房源 {} 经营数据失败: {}", house.getId(), e.getMessage(), e);
            }
        }

        log.info("完成计算 {} 的房源经营数据，共 {} 套房源", yesterday, houses.size());
    }

    private void calculateHouseDailyStats(Long houseId, Long hostId, LocalDate date) {
        HouseDailyStats existStats = houseDailyStatsMapper.selectOne(
                new LambdaQueryWrapper<HouseDailyStats>()
                        .eq(HouseDailyStats::getHouseId, houseId)
                        .eq(HouseDailyStats::getStatDate, date));

        List<OrderInfo> orders = orderInfoMapper.selectList(
                new LambdaQueryWrapper<OrderInfo>()
                        .eq(OrderInfo::getHouseId, houseId)
                        .ne(OrderInfo::getStatus, 4)
                        .le(OrderInfo::getCheckInDate, date)
                        .ge(OrderInfo::getCheckOutDate, date));

        int orderCount = 0;
        int nightCount = 0;
        BigDecimal totalIncome = BigDecimal.ZERO;
        BigDecimal avgPrice = BigDecimal.ZERO;

        for (OrderInfo order : orders) {
            if (order.getCheckInDate().equals(date) && order.getStatus() >= 1) {
                orderCount++;
            }
            if (order.getStatus() >= 1) {
                nightCount++;
                long nights = java.time.temporal.ChronoUnit.DAYS.between(
                        order.getCheckInDate().isAfter(date) ? order.getCheckInDate() : date,
                        order.getCheckOutDate().isBefore(date.plusDays(1)) ? order.getCheckOutDate() : date.plusDays(1)
                );
                BigDecimal dailyPrice = order.getPayAmount().divide(
                        BigDecimal.valueOf(order.getNightCount()), 2, RoundingMode.HALF_UP);
                totalIncome = totalIncome.add(dailyPrice.multiply(BigDecimal.valueOf(nights)));
            }
        }

        if (nightCount > 0) {
            avgPrice = totalIncome.divide(BigDecimal.valueOf(nightCount), 2, RoundingMode.HALF_UP);
        }

        HouseCalendar calendar = houseCalendarMapper.selectOne(
                new LambdaQueryWrapper<HouseCalendar>()
                        .eq(HouseCalendar::getHouseId, houseId)
                        .eq(HouseCalendar::getDate, date));
        int totalStock = calendar != null ? Math.max(calendar.getStock() + nightCount, 1) : 1;
        BigDecimal occupancyRate = BigDecimal.valueOf(nightCount)
                .divide(BigDecimal.valueOf(totalStock), 4, RoundingMode.HALF_UP);

        List<Review> reviews = reviewMapper.selectList(
                new LambdaQueryWrapper<Review>()
                        .eq(Review::getHouseId, houseId)
                        .apply("DATE(create_time) = {0}", date));
        int reviewCount = reviews.size();
        BigDecimal avgRating = reviews.isEmpty() ? BigDecimal.ZERO : reviews.stream()
                .map(r -> BigDecimal.valueOf(r.getRating()))
                .reduce(BigDecimal.ZERO, BigDecimal::add)
                .divide(BigDecimal.valueOf(reviews.size()), 2, RoundingMode.HALF_UP);

        if (existStats != null) {
            existStats.setOrderCount(orderCount);
            existStats.setNightCount(nightCount);
            existStats.setTotalIncome(totalIncome);
            existStats.setAvgPrice(avgPrice);
            existStats.setOccupancyRate(occupancyRate);
            existStats.setReviewCount(reviewCount);
            existStats.setAvgRating(avgRating);
            houseDailyStatsMapper.updateById(existStats);
        } else {
            HouseDailyStats stats = new HouseDailyStats();
            stats.setHouseId(houseId);
            stats.setHostId(hostId);
            stats.setStatDate(date);
            stats.setOrderCount(orderCount);
            stats.setNightCount(nightCount);
            stats.setTotalIncome(totalIncome);
            stats.setAvgPrice(avgPrice);
            stats.setOccupancyRate(occupancyRate);
            stats.setReviewCount(reviewCount);
            stats.setAvgRating(avgRating);
            houseDailyStatsMapper.insert(stats);
        }
    }

    public void recalculateStats(LocalDate startDate, LocalDate endDate) {
        List<House> houses = houseMapper.selectList(new LambdaQueryWrapper<House>()
                .eq(House::getDeleted, 0));

        for (House house : houses) {
            for (LocalDate date = startDate; !date.isAfter(endDate); date = date.plusDays(1)) {
                try {
                    calculateHouseDailyStats(house.getId(), house.getHostId(), date);
                } catch (Exception e) {
                    log.error("重新计算房源 {} {} 经营数据失败: {}", house.getId(), date, e.getMessage(), e);
                }
            }
        }
    }
}
