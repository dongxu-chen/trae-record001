package com.checkin.entity;

import lombok.Data;
import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "user_treasure", uniqueConstraints = {
    @UniqueConstraint(columnNames = {"userId", "treasureId", "period"})
})
public class UserTreasure {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long userId;

    @Column(nullable = false)
    private Long treasureId;

    @Column(nullable = false, length = 20)
    private String period;

    private Boolean claimed = false;

    @Column(name = "claim_time")
    private LocalDateTime claimTime;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
    }
}
