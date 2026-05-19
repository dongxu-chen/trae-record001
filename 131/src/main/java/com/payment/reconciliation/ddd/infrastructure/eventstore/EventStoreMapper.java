package com.payment.reconciliation.ddd.infrastructure.eventstore;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface EventStoreMapper extends BaseMapper<EventStoreEntity> {

    List<EventStoreEntity> selectByAggregateId(@Param("aggregateId") String aggregateId);

    List<EventStoreEntity> selectByAggregateIdAndVersion(@Param("aggregateId") String aggregateId,
                                                          @Param("sinceVersion") Long sinceVersion);

    List<EventStoreEntity> selectByEventType(@Param("eventType") String eventType);

    List<EventStoreEntity> selectAllEvents();

    List<EventStoreEntity> selectByAggregateType(@Param("aggregateType") String aggregateType);
}
