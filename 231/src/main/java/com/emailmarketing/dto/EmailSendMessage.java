package com.emailmarketing.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.io.Serializable;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class EmailSendMessage implements Serializable {
    private Long taskId;
    private Long sendLogId;
    private Long recipientId;
    private String toEmail;
    private String subject;
    private String content;
}
