package com.ratelimit.center.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.ratelimit.center.entity.RateLimitLogEntity;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface RateLimitLogMapper extends BaseMapper<RateLimitLogEntity> {
}
