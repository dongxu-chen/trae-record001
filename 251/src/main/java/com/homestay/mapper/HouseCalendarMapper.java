package com.homestay.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.homestay.entity.HouseCalendar;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDate;
import java.util.List;

@Mapper
public interface HouseCalendarMapper extends BaseMapper<HouseCalendar> {

    List<HouseCalendar> selectByHouseIdAndDateRange(@Param("houseId") Long houseId,
                                                    @Param("startDate") LocalDate startDate,
                                                    @Param("endDate") LocalDate endDate);

    int batchInsert(@Param("list") List<HouseCalendar> list);

    int batchUpdateStock(@Param("houseId") Long houseId,
                         @Param("startDate") LocalDate startDate,
                         @Param("endDate") LocalDate endDate,
                         @Param("stock") int stock);
}
