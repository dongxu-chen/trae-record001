package com.homestay.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("review")
public class Review {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long orderId;

    private Long houseId;

    private Long userId;

    private Long hostId;

    private Integer rating;

    private String content;

    private String images;

    private Integer cleanliness;

    private Integer accuracy;

    private Integer communication;

    private Integer location;

    private Integer checkIn;

    private Integer value;

    private String hostReply;

    private LocalDateTime hostReplyTime;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableLogic
    private Integer deleted;
}
