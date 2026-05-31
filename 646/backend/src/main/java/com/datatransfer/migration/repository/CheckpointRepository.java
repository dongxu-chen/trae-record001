package com.datatransfer.migration.repository;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.datatransfer.migration.model.Checkpoint;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface CheckpointRepository extends BaseMapper<Checkpoint> {
}
