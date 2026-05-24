package com.homestay.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.homestay.entity.Blacklist;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.time.LocalDateTime;

@Mapper
public interface BlacklistMapper extends BaseMapper<Blacklist> {

    @Select("SELECT * FROM blacklist WHERE user_id = #{userId} AND status = 1 " +
            "AND start_time <= #{now} AND (end_time IS NULL OR end_time >= #{now}) " +
            "ORDER BY create_time DESC LIMIT 1")
    Blacklist findActiveBlacklist(@Param("userId") Long userId, @Param("now") LocalDateTime now);

    @Select("SELECT COUNT(*) > 0 FROM blacklist WHERE user_id = #{userId} AND status = 1 " +
            "AND start_time <= #{now} AND (end_time IS NULL OR end_time >= #{now})")
    boolean isUserBlacklisted(@Param("userId") Long userId, @Param("now") LocalDateTime now);
}
