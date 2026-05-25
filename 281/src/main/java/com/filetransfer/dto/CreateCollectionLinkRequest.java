package com.filetransfer.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.time.LocalDateTime;

@Data
public class CreateCollectionLinkRequest {
    @NotBlank(message = "标题不能为空")
    private String title;

    private String description;

    private Long maxFileSize;

    private Integer maxFiles;

    private String password;

    private Integer expireDays = 7;

    private Long userId = 1L;
}
