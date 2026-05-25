package com.ticket.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class AddCommentDTO {

    @NotNull(message = "工单ID不能为空")
    private Long ticketId;

    @NotBlank(message = "评论内容不能为空")
    private String content;

    @NotNull(message = "作者ID不能为空")
    private Long authorId;

    private Boolean internal = false;
}
