package com.homestay.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

@Data
public class OrderCreateDTO {

    @NotNull(message = "房源ID不能为空")
    private Long houseId;

    @NotNull(message = "入住日期不能为空")
    private LocalDate checkInDate;

    @NotNull(message = "退房日期不能为空")
    private LocalDate checkOutDate;

    @NotNull(message = "入住人数不能为空")
    private Integer guestCount;

    @NotNull(message = "联系人姓名不能为空")
    private String contactName;

    @NotNull(message = "联系人电话不能为空")
    private String contactPhone;

    private String remark;

    private Long couponId;

    private List<Long> couponIds;
}
