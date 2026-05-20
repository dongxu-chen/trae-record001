package com.payment.reconciliation.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.payment.reconciliation.entity.FundTransfer;
import org.apache.ibatis.annotations.Param;

public interface FundTransferMapper extends BaseMapper<FundTransfer> {

    FundTransfer selectByRequestId(@Param("requestId") String requestId);
}
