package com.payment.reconciliation.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.payment.reconciliation.entity.TransactionFee;
import org.apache.ibatis.annotations.Param;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

public interface TransactionFeeMapper extends BaseMapper<TransactionFee> {

    List<TransactionFee> selectBySettlementDate(@Param("channelCode") String channelCode,
                                                  @Param("settlementDate") LocalDate settlementDate);

    BigDecimal sumFeeByDateRange(@Param("channelCode") String channelCode,
                                  @Param("startDate") LocalDate startDate,
                                  @Param("endDate") LocalDate endDate);

    int batchInsert(@Param("list") List<TransactionFee> list);
}
