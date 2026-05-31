package com.datatransfer.migration.repository;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.datatransfer.migration.model.TaskLog;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface TaskLogRepository extends BaseMapper<TaskLog> {
}
