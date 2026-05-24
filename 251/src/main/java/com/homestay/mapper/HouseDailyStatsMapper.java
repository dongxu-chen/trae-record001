package com.homestay.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.homestay.entity.HouseDailyStats;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@Mapper
public interface HouseDailyStatsMapper extends BaseMapper<HouseDailyStats> {

    @Select("SELECT stat_date, SUM(order_count) as order_count, SUM(night_count) as night_count, " +
            "SUM(total_income) as total_income, AVG(avg_price) as avg_price, " +
            "AVG(occupancy_rate) as occupancy_rate, SUM(review_count) as review_count, " +
            "AVG(avg_rating) as avg_rating " +
            "FROM house_daily_stats WHERE host_id = #{hostId} " +
            "AND stat_date BETWEEN #{startDate} AND #{endDate} " +
            "GROUP BY stat_date ORDER BY stat_date ASC")
    List<Map<String, Object>> getHostDailyStats(@Param("hostId") Long hostId,
                                                 @Param("startDate") LocalDate startDate,
                                                 @Param("endDate") LocalDate endDate);

    @Select("SELECT stat_date, order_count, night_count, total_income, avg_price, " +
            "occupancy_rate, review_count, avg_rating " +
            "FROM house_daily_stats WHERE house_id = #{houseId} " +
            "AND stat_date BETWEEN #{startDate} AND #{endDate} " +
            "ORDER BY stat_date ASC")
    List<Map<String, Object>> getHouseDailyStats(@Param("houseId") Long houseId,
                                                  @Param("startDate") LocalDate startDate,
                                                  @Param("endDate") LocalDate endDate);

    @Select("SELECT " +
            "COALESCE(SUM(order_count), 0) as total_orders, " +
            "COALESCE(SUM(night_count), 0) as total_nights, " +
            "COALESCE(SUM(total_income), 0) as total_income, " +
            "COALESCE(AVG(avg_price), 0) as avg_price, " +
            "COALESCE(AVG(occupancy_rate), 0) as avg_occupancy, " +
            "COALESCE(AVG(avg_rating), 0) as avg_rating " +
            "FROM house_daily_stats WHERE house_id = #{houseId} " +
            "AND stat_date BETWEEN #{startDate} AND #{endDate}")
    Map<String, Object> getHouseSummary(@Param("houseId") Long houseId,
                                        @Param("startDate") LocalDate startDate,
                                        @Param("endDate") LocalDate endDate);

    @Select("SELECT " +
            "COALESCE(SUM(order_count), 0) as total_orders, " +
            "COALESCE(SUM(night_count), 0) as total_nights, " +
            "COALESCE(SUM(total_income), 0) as total_income, " +
            "COALESCE(AVG(avg_price), 0) as avg_price, " +
            "COALESCE(AVG(occupancy_rate), 0) as avg_occupancy, " +
            "COALESCE(AVG(avg_rating), 0) as avg_rating " +
            "FROM house_daily_stats WHERE host_id = #{hostId} " +
            "AND stat_date BETWEEN #{startDate} AND #{endDate}")
    Map<String, Object> getHostSummary(@Param("hostId") Long hostId,
                                        @Param("startDate") LocalDate startDate,
                                        @Param("endDate") LocalDate endDate);
}
