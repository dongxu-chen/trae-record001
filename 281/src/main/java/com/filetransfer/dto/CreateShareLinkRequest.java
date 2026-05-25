package com.filetransfer.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CreateShareLinkRequest {
    @NotNull(message = "文件ID不能为空")
    private Long fileId;

    private String title;

    private Boolean enableWatermark = true;

    private String watermarkText;

    private Boolean enableDownload = true;

    private Boolean enablePreview = true;

    private Integer maxViews;

    private String password;

    private Integer expireDays = 7;

    private Long userId = 1L;
}
