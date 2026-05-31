package com.checkin.entity;

import lombok.Data;
import javax.persistence.*;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "checkin_share")
public class CheckinShare {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long userId;

    @Column(nullable = false)
    private LocalDate shareDate;

    @Column(length = 50)
    private String sharePlatform;

    private String shareContent;

    private String shareImage;

    private Integer viewCount = 0;

    private Integer likeCount = 0;

    private Boolean rewardClaimed = false;

    private String rewardType;

    private Integer rewardValue;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
    }
}
