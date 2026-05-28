package com.voting.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotEmpty;
import javax.validation.constraints.NotNull;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class CreateVoteRequest {

    @NotBlank(message = "投票标题不能为空")
    private String title;

    private String description;

    @NotBlank(message = "投票类型不能为空")
    private String type;

    private Integer minSelect = 1;
    private Integer maxSelect = 1;
    private Integer minScore = 1;
    private Integer maxScore = 5;

    private Boolean requireVoteCode = false;
    private Boolean allowAnonymous = true;

    private LocalDateTime startTime;
    private LocalDateTime endTime;

    @NotEmpty(message = "投票选项不能为空")
    private List<String> options;

    private String createdBy;
}
