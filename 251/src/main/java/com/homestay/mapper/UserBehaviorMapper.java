package com.homestay.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.homestay.entity.UserBehavior;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.time.LocalDateTime;

@Mapper
public interface UserBehaviorMapper extends BaseMapper<UserBehavior> {

    @Select("SELECT COUNT(*) FROM user_behavior WHERE user_id = #{userId} " +
            "AND behavior_type = #{behaviorType} AND create_time >= #{startTime}")
    int countUserBehavior(@Param("userId") Long userId,
                          @Param("behaviorType") Integer behaviorType,
                          @Param("startTime") LocalDateTime startTime);
}
