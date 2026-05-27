package com.platform.points.vo;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class UserLevelVO {

    private Long userId;

    private Long currentLevelId;

    private String currentLevelCode;

    private String currentLevelName;

    private Integer currentLevelOrder;

    private String levelIcon;

    private Double discountRate;

    private String levelPrivileges;

    private Integer totalPoints;

    private Integer levelPoints;

    private Integer nextLevelPoints;

    private String nextLevelName;

    private Integer pointsToNextLevel;

    private Double progressPercent;

    private LocalDateTime levelUpTime;
}
