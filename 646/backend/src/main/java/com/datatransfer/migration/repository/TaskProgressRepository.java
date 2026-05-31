package com.datatransfer.migration.repository;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.datatransfer.migration.model.TaskProgress;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface TaskProgressRepository extends BaseMapper<TaskProgress> {
}
