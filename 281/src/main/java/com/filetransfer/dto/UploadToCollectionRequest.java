package com.filetransfer.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class UploadToCollectionRequest {
    @NotBlank(message = "收集码不能为空")
    private String linkCode;

    private String uploaderName;

    private String uploaderEmail;

    private String remark;

    private String password;
}
