package com.homestay.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("house_daily_stats")
public class HouseDailyStats {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long houseId;

    private Long hostId;

    private LocalDate statDate;

    private Integer orderCount;

    private Integer nightCount;

    private BigDecimal totalIncome;

    private BigDecimal avgPrice;

    private BigDecimal occupancyRate;

    private Integer reviewCount;

    private BigDecimal avgRating;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
