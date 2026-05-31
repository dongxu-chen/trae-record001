package com.checkin.entity;

import lombok.Data;
import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "checkin_stats")
public class CheckinStats {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long userId;

    @Column(nullable = false, length = 20)
    private String periodType;

    @Column(nullable = false, length = 20)
    private String period;

    private Integer continuousDays = 0;

    private Integer totalDays = 0;

    private Integer recheckCount = 0;

    @Column(name = "update_time")
    private LocalDateTime updateTime;

    @PreUpdate
    protected void onUpdate() {
        updateTime = LocalDateTime.now();
    }
}
