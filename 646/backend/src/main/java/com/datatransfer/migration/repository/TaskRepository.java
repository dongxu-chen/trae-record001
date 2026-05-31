package com.datatransfer.migration.repository;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.datatransfer.migration.model.Task;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface TaskRepository extends BaseMapper<Task> {
}
