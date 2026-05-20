package com.pushplatform.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.pushplatform.entity.PushTask;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface PushTaskMapper extends BaseMapper<PushTask> {
}
