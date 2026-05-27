package com.platform.points.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.platform.points.entity.UserLevel;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface UserLevelMapper extends BaseMapper<UserLevel> {

    @Select("SELECT * FROM user_level WHERE user_id = #{userId} AND deleted = 0")
    UserLevel selectByUserId(@Param("userId") Long userId);
}
