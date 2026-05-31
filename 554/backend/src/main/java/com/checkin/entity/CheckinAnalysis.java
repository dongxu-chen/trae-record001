package com.checkin.entity;

import lombok.Data;
import javax.persistence.*;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "checkin_analysis")
public class CheckinAnalysis {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 20)
    private String periodType;

    @Column(nullable = false)
    private LocalDate analysisDate;

    private Long totalUsers;

    private Long checkedInUsers;

    private Double checkinRate;

    private Integer maxContinuousDays;

    private Integer avgContinuousDays;

    private Integer churnDay;

    private Double churnRate;

    private Long newUsers;

    private Long lostUsers;

    private Long recheckCount;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
    }
}
