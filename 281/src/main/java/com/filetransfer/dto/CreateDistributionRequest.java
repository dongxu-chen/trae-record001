package com.filetransfer.dto;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Data
public class CreateDistributionRequest {
    private String title;

    private String message;

    @NotNull(message = "文件列表不能为空")
    @NotEmpty(message = "文件列表不能为空")
    private List<Long> fileIds;

    private List<RecipientDTO> recipients;

    private Integer expireDays = 7;

    private Long userId = 1L;

    @Data
    public static class RecipientDTO {
        private String type;
        private String identifier;
        private String name;
    }
}
