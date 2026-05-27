package com.platform.points.vo;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class UserPointsVO {

    private Long userId;

    private Integer totalPoints;

    private Integer availablePoints;

    private Integer frozenPoints;

    private LocalDateTime updateTime;
}
