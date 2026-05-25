package com.taskscheduler.core.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.taskscheduler.common.entity.ExecutorInfo;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface ExecutorInfoMapper extends BaseMapper<ExecutorInfo> {
}
