package com.payment.reconciliation.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.payment.reconciliation.entity.ReversalTask;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface ReversalTaskMapper extends BaseMapper<ReversalTask> {

    List<ReversalTask> selectPendingTasks(@Param("status") Integer status, @Param("limit") Integer limit);
}
