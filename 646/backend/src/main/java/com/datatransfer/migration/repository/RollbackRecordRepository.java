package com.datatransfer.migration.repository;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.datatransfer.migration.model.RollbackRecord;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface RollbackRecordRepository extends BaseMapper<RollbackRecord> {
}
