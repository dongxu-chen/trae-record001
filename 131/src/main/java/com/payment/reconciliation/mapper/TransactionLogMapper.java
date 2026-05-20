package com.payment.reconciliation.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.payment.reconciliation.entity.TransactionLog;
import org.apache.ibatis.annotations.Param;

public interface TransactionLogMapper extends BaseMapper<TransactionLog> {

    TransactionLog selectByTransactionId(@Param("transactionId") String transactionId);
}
