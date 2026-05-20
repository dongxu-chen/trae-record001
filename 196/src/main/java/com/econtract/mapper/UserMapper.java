package com.econtract.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.econtract.entity.User;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface UserMapper extends BaseMapper<User> {
}
