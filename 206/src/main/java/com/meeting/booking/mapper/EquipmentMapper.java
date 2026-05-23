package com.meeting.booking.mapper;

import com.meeting.booking.entity.Equipment;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface EquipmentMapper {

    Equipment selectById(@Param("id") Long id);

    List<Equipment> selectAll();

    List<Equipment> selectByRoomId(@Param("roomId") Long roomId);

    List<Equipment> selectByTypes(@Param("types") List<String> types);

    int insert(Equipment equipment);

    int update(Equipment equipment);

    int deleteById(@Param("id") Long id);
}
