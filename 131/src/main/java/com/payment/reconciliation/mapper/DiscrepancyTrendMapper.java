package com.payment.reconciliation.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.payment.reconciliation.entity.DiscrepancyTrend;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDate;
import java.util.List;

public interface DiscrepancyTrendMapper extends BaseMapper<DiscrepancyTrend> {

    List<DiscrepancyTrend> selectByDateRange(@Param("channelCode") String channelCode,
                                               @Param("startDate") LocalDate startDate,
                                               @Param("endDate") LocalDate endDate);

    DiscrepancyTrend selectByDateAndChannel(@Param("statisticsDate") LocalDate statisticsDate,
                                             @Param("channelCode") String channelCode);
}
