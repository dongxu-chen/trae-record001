package com.payment.reconciliation.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.payment.reconciliation.entity.ChannelTransaction;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface ChannelTransactionMapper extends BaseMapper<ChannelTransaction> {

    List<ChannelTransaction> selectUnmatchedByReconciliationId(@Param("reconciliationId") Long reconciliationId);

    int batchInsert(@Param("list") List<ChannelTransaction> list);
}
