package com.payment.reconciliation.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.payment.reconciliation.entity.SettlementMonitor;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDate;
import java.util.List;

public interface SettlementMonitorMapper extends BaseMapper<SettlementMonitor> {

    List<SettlementMonitor> selectByDateRange(@Param("channelCode") String channelCode,
                                               @Param("startDate") LocalDate startDate,
                                               @Param("endDate") LocalDate endDate);

    List<SettlementMonitor> selectDelayedSettlements(@Param("alertLevel") Integer alertLevel);
}
