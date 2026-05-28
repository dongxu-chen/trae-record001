package com.voting.dto;

import lombok.Data;

import javax.validation.constraints.NotNull;
import java.util.List;

@Data
public class SubmitVoteRequest {

    @NotNull(message = "投票ID不能为空")
    private Long voteId;

    private List<Long> optionIds;

    private Long optionId;

    private Integer score;

    private String voteCode;

    private String deviceFingerprint;

    private String anonymousProof;
}
