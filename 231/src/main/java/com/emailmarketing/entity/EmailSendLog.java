package com.emailmarketing.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("email_send_log")
public class EmailSendLog {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long taskId;
    private Long recipientId;
    private String email;
    private Integer sendStatus;
    private String errorMsg;
    private Integer opened;
    private LocalDateTime openTime;
    private Integer clicked;
    private LocalDateTime clickTime;
    private Integer unsubscribed;
    private LocalDateTime unsubscribeTime;
    private LocalDateTime sentAt;
    private LocalDateTime createdAt;
}
