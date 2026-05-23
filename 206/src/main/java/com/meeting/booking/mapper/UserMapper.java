package com.meeting.booking.mapper;

import com.meeting.booking.entity.User;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface UserMapper {

    User selectById(@Param("id") Long id);

    User selectByUsername(@Param("username") String username);

    List<User> selectAll();

    int insert(User user);

    int update(User user);

    int deleteById(@Param("id") Long id);
}
