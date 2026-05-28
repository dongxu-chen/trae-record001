package com.voting.dto;

import lombok.Data;

import java.util.List;

@Data
public class VoteResultDTO {

    private Long voteId;
    private String title;
    private String type;
    private Long totalVotes;
    private List<OptionResult> options;

    @Data
    public static class OptionResult {
        private Long optionId;
        private String content;
        private Long voteCount;
        private Double percentage;
        private Double avgScore;
    }
}
