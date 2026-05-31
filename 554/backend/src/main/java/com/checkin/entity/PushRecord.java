package com.checkin.entity;

import lombok.Data;
import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "push_record")
public class PushRecord {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long userId;

    @Column(nullable = false, length = 50)
    private String pushType;

    @Column(nullable = false, length = 20)
    private String pushChannel;

    private String title;

    @Column(length = 500)
    private String content;

    private Boolean success = false;

    private String errorMessage;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @Column(name = "send_time")
    private LocalDateTime sendTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
    }
}
