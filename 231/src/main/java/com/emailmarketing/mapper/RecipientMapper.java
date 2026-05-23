package com.emailmarketing.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.emailmarketing.entity.Recipient;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface RecipientMapper extends BaseMapper<Recipient> {
}
